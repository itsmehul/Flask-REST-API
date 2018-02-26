from flask import Flask, jsonify, make_response, abort, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import json
import datetime
import jwt
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY']='Linda'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:toor@localhost/test'
db = SQLAlchemy(app)
ma= Marshmallow(app)

#USER MODEL
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(50),unique=True)
    username = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(80))
    admin = db.Column(db.Boolean)

    def __init__(self, pid, username, email, password, admin):
        self.public_id = pid
        self.username = username
        self.email = email
        self.password = password
        self.admin = admin

    def ___repr__(self):
        return '<User %r>' % self.username

#TASK MODEL
class Tasks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    title = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(120), unique=True)
    done = db.Column(db.String(10))

    def __init__(self, id, title, description, done):
        self.user_id = id
        self.title = title
        self.description = description
        self.done = done

class UserSchema(ma.ModelSchema):
    class Meta:
        model = User

class TasksSchema(ma.ModelSchema):
    class Meta:
        model = Tasks

#TOKEN VERIFICATION FOR USER DECORATOR | returns user instance for that token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token=None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        
        if not token:
            return jsonify({'message':'Token is missing!'}),401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            create_user = User.query.filter_by(public_id=data['public_id']).first()
            if not create_user:
                return jsonify({'message':'User not found'})
        except:
            return jsonify({'message':'Token is invalid'}), 401

        return f(create_user, *args, **kwargs)
    return decorated

#GENERATES TOKEN 
@app.route('/login')
def login():
    auth=request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate':'Basic realm="Login required"'})

    user=User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate':'Basic realm="Login required"'})

    if check_password_hash(user.password, auth.password):
        token = jwt.encode({'public_id': user.public_id,'exp': datetime.datetime.utcnow()+datetime.timedelta(minutes=120)},app.config['SECRET_KEY'])
        return jsonify({'token': token.decode('UTF-8')})
    


#USER ALL USERS
@app.route('/users')
@token_required
def get_all_users(current_user):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that operation'})

    users = User.query.all()
    output=[]
    for user in users:
        user_data ={}
        user_data['public_id'] = user.public_id
        user_data['username'] = user.username
        user_data['email'] = user.email
        output.append(user_data)

    # return jsonify({'Users':output})
    return jsonify({'Users':current_user.id})

#GET USER
@app.route('/user/<public_id>', methods=['GET'])
@token_required
def get_one_user(current_user,public_id):

    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that operation'})

    user = User.query.filter_by(public_id=public_id).first()
    if not user:
        return jsonify({'message':'User not found'})
    user_data ={}
    user_data['public_id'] = user.public_id
    user_data['username'] = user.username
    user_data['email'] = user.email
    return jsonify({'User':user_data})   
    

#UPDATE USER TO ADMIN
@app.route('/user/<public_id>', methods=['PUT'])
@token_required
def update_user(current_user,public_id):
    
    if not current_user.admin:
        return jsonify({'message': 'Cannot perform that operation'})

    user = User.query.filter_by(public_id=public_id).first()
    if not user:
        return jsonify({'message':'User not found'})
    
    user.admin= True
    db.session.commit()

    return jsonify({'message':'User promoted to admin'})   

#ADD USER
@app.route('/user', methods=['POST'])
def create_user():
   
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'],method='sha256')
    new_user = User(str(uuid.uuid4()),data['username'],data['email'],hashed_password,False)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message':'User added'})  

#DELETE USER
@app.route('/user/<public_id>', methods=['DELETE'])
@token_required
def delete_user(current_user,public_id):

    user = User.query.filter_by(public_id=public_id).first()
    if not user:
        return jsonify({'message':'User not found'})
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message':'User has been deleted'})    

#GET ALL TASKS
@app.route('/tasks', methods=['GET'])
@token_required
def get_all_tasks(current_user):

    tasks = Tasks.query.filter_by(name=current_user.username).all()
    tasks_schema = TasksSchema(many=True)
    res = tasks_schema.dump(tasks).data
    return jsonify({'Tasks':res})

#GET TASK
@app.route('/task/<int:task_id>', methods=['GET'])
@token_required
def get_one_task(current_user,task_id):

    task = [task for task in tasks if task['id'] == task_id]
    return jsonify({'task': task[0]})

#Because our server should only be resonsing in json format we prevent the body to render a 404 template
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

#CREATE TASK
@app.route('/tasks', methods=['POST'])
@token_required
def create_task(current_user):
    task = Tasks(
        current_user.id,
        request.json['title'],
        request.json['description'],
        False)
    db.session.add(task)
    db.session.commit()
    return jsonify({'result': 'success'})

#UPDATE TASK
@app.route('/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user,task_id):

    task = Tasks.query.filter_by(id=task_id).first()
    if not task:
        return jsonify({'message':'Task not found'})

    if 'title' in request.json:
        task.title = request.json['title']
    if 'description' in request.json:
        task.description = request.json['description']
    if 'done' in request.json:
        task.done = request.json['done']
    
    db.session.commit()
    return jsonify({'task': 'updated'})

#DELETE TASK
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(current_user,task_id):
    task = Tasks.query.filter_by(id=task_id).first()
    db.session.delete(task)
    db.session.commit()
    return jsonify({'result': True})



if __name__ == '__main__':
    app.run(debug=True)
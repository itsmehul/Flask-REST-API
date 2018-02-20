from flask import Flask, jsonify, make_response, abort, request, url_for
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:toor@localhost/test'
db = SQLAlchemy(app)
ma= Marshmallow(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def ___repr__(self):
        return '<User %r>' % self.username

class Tasks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(120), unique=True)
    done = db.Column(db.String(10))

    def __init__(self, username, email):
        self.title = title
        self.description = description
        self.done = done

class UserSchema(ma.ModelSchema):
    class Meta:
        model = User

class TasksSchema(ma.ModelSchema):
    class Meta:
        model = Tasks

#List of dictionaries
tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

#User auth logic
auth = HTTPBasicAuth()



@auth.get_password
def get_password(username):
    if username == 'miguel':
        return 'python'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)

@app.route('/users')
def index():
    myUser = User.query.all()
    user_schema = UserSchema(many=True)
    res = user_schema.dump(myUser).data
    return jsonify({'User':res})

@app.route('/todo/api/v1.0/tasks', methods=['GET'])
#Add decorator to those routes you wish to guard
@auth.login_required
def get_tasks():
    #Executes the make_public_task method for every task in tasks
    return jsonify({'tasks': [make_public_task(task) for task in tasks]})

#Return data of a single task
@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})

#Because our server should only be resonsing in json format we prevent the body to render a 404 template
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    #request.json stores all the info from the request in a json format
    if not request.json or not 'title' in request.json:
        abort(400)
    #Define the expected object structure
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    #Pass the data object into the data structure
    tasks.append(task)
    return jsonify({'task': task}), 201

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    #Look for task in tasks
    task = [task for task in tasks if task['id'] == task_id]
    #Checks if there exist any task
    if len(task) == 0:
        abort(404)
    #Checks if request is of json type
    if not request.json:
        abort(400)
    #Checks for title, description, done
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    #Updates values by overwriting
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify({'result': True})

#Creates a new_task with all fields but ID
def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            new_task['uri'] = url_for('get_task', task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task


if __name__ == '__main__':
    app.run(debug=True)
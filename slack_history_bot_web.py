import datetime
from flask import Flask
from flask import render_template
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config['MONGO_DBNAME'] = 'slack_history_db'
mongo = PyMongo(app)


class Message(object):
    def __init__(self, time_stamp, user, message):
        self.ts = time_stamp
        self.user = user
        self.message = message


class User(object):
    def __init__(self, user):
        if 'profile' in user:
            profile = user['profile']
            self.first_name = profile['first_name'] if 'first_name' in profile else "--"
            self.last_name = profile['last_name'] if 'last_name' in profile else "--"
        else:
            self.first_name = ""
            self.last_name = ""
        self.full_name = "{} {}".format(self.first_name, self.last_name)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/history/<channel>')
def get_history(channel):
    history = mongo.db.history.find({u'channel': channel})
    users = mongo.db.users.find()

    usrs = {}
    for user in users:
        usrs[user['id']] = User(user)

    messages = []
    for record in history:
        dt = datetime.datetime.fromtimestamp(float(record['ts']))
        messages.append(Message(dt, usrs[record['user']].full_name, record['text']))

    return render_template('index.html', history=messages)


if __name__ == '__main__':
    app.run()

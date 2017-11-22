from flask import Flask,jsonify,request,render_template,make_response
from logging import FileHandler,WARNING,ERROR
from pymongo import MongoClient
from flask_mail import Mail,Message
import jwt
import datetime
from functools import wraps
import configparser


Config = configparser.ConfigParser()
Config.read("task.ini")

app=Flask(__name__)
app.config['SECRECT_KEY']=Config.get('keys','secrect_key')

file_handler=FileHandler('errorlog.txt')
file_handler.setLevel(WARNING)

app.logger.addHandler(file_handler)

client=MongoClient(Config.get('mongo','host'))

db=client.tasks

app.config.update(
    debug=True,
    # EMAIL SETTINGS
    MAIL_SERVER=Config.get('mail','mail_server'),
	MAIL_PORT=Config.get('mail','mail_port'),
	MAIL_USE_SSL=Config.get('mail','mail_use_ssl'),
	MAIL_USERNAME = Config.get('mail','mail_username'),
	MAIL_PASSWORD = Config.get('mail','mail_password')
)

mail=Mail(app)

def token_required(f):
    wraps(f)
    def decorated(*args,**kwargs):
        token=request.args.get('token')
        #token=request.headers['token']
        if not token:
            return jsonify({'message':'token is missing'}),403
        try:
            data=jwt.decode(token,app.config['SECRECT_KEY'])
        except:
            return jsonify({'message':'token is invalid'}),403

        return f(*args,**kwargs)

    return decorated

@app.route('/sendmail',methods=['POST'])
def sendmail():
    try:
        msg=Message("Todo List for this month",sender="pbprathi@gmail.com",recipients=["pbprathi@gmail.com"])
        task=db.tasks
        html="<html> <body><p>Hey Bhageerath babu prathi,<br><br>Please find the monthly expenses list, plan accordingly</p</body>"
        html+="""<table style="width:100%" border=1><caption>Monthly Todo List</caption><tr><th>task_id</th><th>title</th> <th>description</th><th>done</th></tr>"""
        for t in task.find():
            html+="<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(t['task_id'],t['title'],t['description'],t['done'])
        html+="</table></html>"
        msg.html= html
        mail.send(msg)
        return 'Mail sent!'
    except Exception as e:
        return(str(e))

@app.route('/tasks',methods=['GET'])
def get_all_tasks():
    task=db.tasks
    output=[]
    for t in task.find():
        output.append({'task_id':t['task_id'],'title':t['title'],'description':t['description'],'done':t['done']})

    return jsonify({'results':output}),200

@app.route('/task/<task_id>',methods=['GET'])
def get_task(task_id):
    task=db.tasks
    output=[]
    t=task.find_one({'task_id':task_id})
    if t:
        output={'task_id':t['task_id'],'title':t['title'],'description':t['description'],'done':t['done']}
    else:
        return {'message':'No document found'},404
    return jsonify({'result':output})

@app.route('/task',methods=['POST'])
def post_task():
    task=db.tasks
    output=[]
    taskobj_id=task.insert({'task_id':request.json['task_id'],
    'title':request.json['title'],'description':request.json['description'],
    'done':request.json['done']})

    inserted_doc=task.find_one({'_id':taskobj_id})
    output={'task_id':inserted_doc['task_id'],'title':inserted_doc['title'],'description':inserted_doc['description'],'done':inserted_doc['done']}
    return jsonify({'result':output}),200

@app.route('/task/<task_id>',methods=['PUT'])
def put_task(task_id):
    task=db.tasks
    output=[]
    q=task.find_one({'task_id':task_id})
    if q:
        task.update({'task_id':task_id},{'task_id':request.json['task_id'],'title':request.json['title'],'description':request.json['description'],
        'done':request.json['done']})
        updated_task=task.find_one({'task_id':task_id})
        output={'task_id':updated_task['task_id'],'title':updated_task['title'],'description':updated_task['description'],'done':updated_task['done']}
    else:
        taskobj_id=task.insert({'task_id':request.json['task_id'],'title':request.json['title'],'description':request.json['description'],'done':request.json['done']})
        inserted_doc=task.find_one({'_id':taskobj_id})
        output={'task_id':inserted_doc['task_id'],'title':inserted_doc['title'],'description':inserted_doc['description'],'done':inserted_doc['done']}

    return jsonify({'result':output}),200

@app.route('/task/<task_id>',methods=['DELETE'])
def del_task(task_id):
    task=db.tasks
    task.remove({'task_id':task_id})
    return jsonify({'message':'Task deleted'}),200

@app.route('/register',methods=['POST'])
def user_register():
    user=db.users
    auth=request.authorization
    if not user.find_one({'username':auth.username}):
        user_objectid=user.insert({'username':auth.username,'password':auth.password})

        if user_objectid:
            return jsonify({'message':'User successfully regsitered'}),200
        else:
            return jsonify({'message':'User registration failed'}),400
    else:
        return jsonify({'message':'User already registerd'})

@app.route('/login')
def login():
    user=db.users
    auth=request.authorization
    usercred=user.find_one({'username':auth.username,'password':auth.password})
    if auth and auth.username==usercred['username'] and auth.password==usercred['password']:
        token=jwt.encode({'user':usercred['username'],'pwd':usercred['password'],'exp':datetime.datetime.utcnow()+datetime.timedelta(minutes=30)},app.config['SECRECT_KEY'])
        return jsonify({'token':token.decode('UTF-8')})
    else:
        return make_response('Could not verify',401,{'WWW-Authenticate:Basic realm="Login Required"'})

if __name__=='__main__':
    app.run(debug=True)

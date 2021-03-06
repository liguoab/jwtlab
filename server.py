from flask import Flask, render_template, request, jsonify, g
from functools import wraps
from datetime import datetime, timedelta

import json

from config import token_timeout, jwt_algorithm

import jwt
from jwt.exceptions import DecodeError, ExpiredSignature

app = Flask(__name__, template_folder='static')
try:
	# you may not commit secret_key.txt
	app.config['SECRET_KEY'] = open('secret_key.txt', 'rb').read()
except IOError:
	import random
	app.config['SECRET_KEY'] = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
	secret = file('secret_key.txt', 'w')
	secret.write(app.config['SECRET_KEY'])
	secret.close()

# users data
users = json.loads(open('users.json', 'rb').read().strip())

# decorator that makes an endpoint require a valid jwt token
def jwt_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if not request.headers.get('Authorization'):
			return jsonify(message='Missing authorization header'), 401
		try:
			payload = parse_token(request)
			g.user = payload['sub']
		except DecodeError:
			return jsonify(message='Token is invalid'), 401
		except ExpiredSignature:
			return jsonify(message='Token has expired'), 401
		return f(*args, **kwargs)
	return decorated_function


# validate user and password agains users 'database'
def authenticate(user, pwd):
	for usr in users:
		if usr['email'] == user and usr['password'] == pwd:
			return create_token(usr)
	return False


# creates a jwt token loaded with user data
def create_token(user):
	payload = {
		# subject
		'sub': user['name'],
		# issued at
		'iat': datetime.utcnow(),
		# expiry
		'exp': datetime.utcnow() + timedelta(minutes=token_timeout)
	}
	token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm=jwt_algorithm)
	return token.decode('unicode_escape')


def parse_token(req):
	token = req.headers.get('Authorization').split()[1]
	return jwt.decode(token, app.config['SECRET_KEY'], algorithms=jwt_algorithm)


@app.route('/', methods=['GET', ])
def home():
	return render_template('index.html')


# curl -X GET http://localhost:5000/public"
@app.route('/public', methods=['GET'])
def public():
	return "This is the public area.\n"


# curl -H "Content-Type: application/json" -X POST -d '{"email":"scott@gmail.com", "password":"12345"}' http://localhost:5000/signin
@app.route('/signin', methods=['POST'])
def login():
	data = request.get_json()
	encoded = authenticate(data['email'], data['password'])
	if encoded:
		return encoded
	else:
		return "Unauthorized", 401


# curl -X GET http://localhost:5000/restricted -H "Authorization: Bearer $token"
@app.route('/restricted', methods=['GET'])
@jwt_required
def restricted():
	return "Welcome %s. This message is restricted. \n" % g.user

if __name__ == '__main__':
    app.run(debug=True)

import os
from datetime import timedelta

import redis
from flask import Flask, request, jsonify, make_response, abort
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, current_user, get_jwt
from src.models import User, db, db_setup, Group,Group_members
from werkzeug.security import generate_password_hash


ACCESS_EXPIRES = timedelta(hours=1)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["JWT_SECRET_KEY"] = "dd9244b79f969a0f297442075b9147d55ebf1c6f4cd283f5b1b18105c49486dcce4eb8510fe7d72954977307d81a0730a057dea573e3e8767535140e608845f9"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_EXPIRES
db_setup(app)
jwt = JWTManager(app)


@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()


# Setup redis connection for storing the blocklisted tokens
jwt_redis_blocklist = redis.StrictRedis(
    host="localhost", port=6379, db=0,decode_responses=True
)


# Callback function to check if a JWT exists in the redis blocklist
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token_in_redis = jwt_redis_blocklist.get(jti) 
    return token_in_redis is not None


@app.route("/", methods=["GET"])
def index():
    return "Welcome to the World of Web Services"


# Only ADMIN can add users, so this API should be accessed only by ADMIN users.
@app.route('/user', methods=['POST'])
@jwt_required()
def new_user():
    role = current_user.role
    if role == 'admin':
        username = request.json.get('username')
        password = request.json.get('password')
        user = User.query.filter_by(name=username).first()
        if user:
            return jsonify({
                "status": "fail",
                "msg": user.name + " already exists"
            })

        user = User(name=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({
            "user": username,
            "status": "successfully added"
        })
    return jsonify({
        "status": "fail",
        "msg": "Only admin can add new user"
    })


# Only ADMIN can add users, so this API should be accessed only by ADMIN users.
@app.route('/user', methods=['PATCH'])
@jwt_required()
def update_user():
    role = current_user.role
    if role == 'admin':
        body = request.get_json()
        if 'username' not in body:
            abort(404)
        user = User.query.filter_by(name=body['username']).one_or_none()
        if user is None:
            abort(404)
        if 'role' in body:
            user.role = body['role']
        if 'password' in body:
            password = body['password']
            user.password_hash = generate_password_hash(password, method='sha256')

        db.session.add(user)
        db.session.commit()
        return jsonify({
            "status": "success",
            "msg": "User updated Successfully"
        })
    return jsonify({
        "status": "fail",
        "msg": "Only Admin can update user details"
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    user = User.query.filter_by(name=username).first()
    print(user.name)
    print(user.password_hash)
    if not user:
        return make_response(
            'Could not verify',
            401,
            {'WWW-Authenticate': 'Basic realm = "User does not exist !!"'}
        )
    if user.check_password(password):
        access_token = create_access_token(identity=user)
        return jsonify(access_token=access_token)
    return make_response(
        'Could not verify user',
        403,
        {'WWW-Authenticate': 'Basic realm ="Wrong Password !!"'}
    )


@app.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    jwt_redis_blocklist.set(jti, "", ex=ACCESS_EXPIRES)
    return jsonify({
        "status": "success",
        "msg": "User logged out and Access token revoked"
    })

@app.route("/group", methods=["POST"])
@jwt_required()
def create_group():
    group_name = request.json.get("group_name", None)
    group = Group.query.filter_by(name=group_name).first()
    if group:
        return jsonify({
            "status": "fail",
            "msg": group.name + " already exists"
        })
    group = Group(name=group_name, creator_id=current_user.id)
    db.session.add(group)
    db.session.commit()
    return jsonify({
        "group": group_name,
        "status": "success"
    })


@app.route("/group", methods=["DELETE"])
@jwt_required()
def delete_group():
    group_name = request.json.get("group_name", None)
    group = Group.query.filter_by(name=group_name).one_or_none()
    if group is None:
        return jsonify({
            "status": "fail",
            "msg": group_name + " does not exists"
        })
    if group.creator_id != current_user.id:
        return jsonify({
            "status": "fail",
            "msg": "You are not authorized to delete"
        })
    else:
        Group.query.filter_by(name=group_name).delete()
        db.session.commit()
        return jsonify({
            "msg": group_name + " deleted",
            "status": "success"
        })

@app.route("/group/members", methods=["POST"])
@jwt_required()
def add_group_member():
    member_name = request.json.get("member_name", None)
    group_name = request.json.get("group_name",None)
    groupmembers = Group_members.query.filter_by(name=member_name).first()
    group = Group_members.query.filter_by(groupname=group_name).first()
    if groupmembers and group:
            return jsonify({
            "status": "fail",
            "msg": groupmembers.name + " already exists in the group " +  group.groupname
        }) 
    groupmembers = Group_members(name=member_name, groupname= group_name)
    db.session.add(groupmembers)
    db.session.commit()
    return jsonify({
        "group": member_name,
        "status": "success"
    })

@app.route("/users/search", methods=["POST"])
@jwt_required()
def search_users():
    search_user_term = request.form.get('search_term', '')
    searched_user_list = User.query.filter(User.name.ilike(f'%{search_user_term}%')).all()
    print(searched_user_list)
    user_count = len(searched_user_list)
    user_data = []
    for user in searched_user_list:
        user_data.append(user.name)

    return jsonify({
            "count": user_count,
            "user_data": user_data
        })


if __name__ == "__main__":
    app.run()

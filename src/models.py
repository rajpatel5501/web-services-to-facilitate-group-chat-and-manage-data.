from collections import UserList
import os
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Constraint, ForeignKey, ForeignKeyConstraint
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_URL = 'postgresql://postgres:12345@localhost:5432/chat_db'
db = SQLAlchemy()


def db_setup(app, database_path=DATABASE_URL):
    app.config['SQLALCHEMY_DATABASE_URI'] = database_path
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)
    migrate = Migrate(app, db)
    db.create_all()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(10))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Group(db.Model):
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    creator_id = db.Column(db.Integer)
    group_member = db.relationship('Group_members', uselist=False)

class Group_members(db.Model):
    __tablename__ = 'groupmembers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    groupname = db.Column (db.String(64),db.ForeignKey("group.name"))


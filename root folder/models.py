from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))



class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    lower_limit = db.Column(db.Float)
    upper_limit = db.Column(db.Float)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'))

    value = db.Column(db.Float)
    flag = db.Column(db.String(10))
    interpretation = db.Column(db.String(200))

    patient = db.relationship('Patient')
    test = db.relationship('Test')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
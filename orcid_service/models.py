# -*- coding: utf-8 -*-
"""
    myads_service.models
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the users (users) of AdsWS
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import synonym

db = SQLAlchemy() # must be run in the context of a flask application

class User(db.Model):
    __bind_key__ = 'orcid'
    __tablename__ = 'users'
    
    orcid_id = db.Column(db.String(255), primary_key=True)
    access_token = db.Column(db.String(255))
    created = db.Column(db.TIMESTAMP)
    updated = db.Column(db.TIMESTAMP)
    profile = db.Column(db.Text)
    info = db.Column(db.Text)
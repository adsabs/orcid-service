# -*- coding: utf-8 -*-
"""
    myads_service.models
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the users (users) of AdsWS
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import synonym
import json

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
    
    def toJSON(self):
        """Returns value formatted as python dict."""
        return {
            'orcid_id': self.orcid_id,
            'access_token': self.access_token,
            'created': self.created and self.created.isoformat() or None,
            'updated': self.updated and self.updated.isoformat() or None,
            'profile': self.profile and json.loads(self.profile) or None,
            'info': self.info and json.loads(self.info) or None
        }
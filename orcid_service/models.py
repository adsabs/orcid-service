# -*- coding: utf-8 -*-
"""
    myads_service.models
    ~~~~~~~~~~~~~~~~~~~~~

    Models for the users (users) of AdsWS
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, TIMESTAMP, Text
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    orcid_id = Column(String(255), primary_key=True)
    access_token = Column(String(255))
    created = Column(TIMESTAMP)
    updated = Column(TIMESTAMP)
    profile = Column(Text)
    info = Column(Text)
    
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
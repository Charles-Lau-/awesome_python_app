#!/usr/bin/env python
#-*- coding:utf-8 -*-
import time,uuid
from transwarp.db import get_id
from transwarp import db
from transwarp.orm import Model,StringField,BooleanField,FloatField,TextField

class  User(Model):
    __table__ = 'users'
    id = StringField(primary_key=True,default = get_id,updatable=False)
    email = StringField(updatable=False)
    password = StringField()
    admin = BooleanField()
    name =  StringField()
    created_at = FloatField(updatable=False,default = time.time)


class Blog(Model):
    __table__ = 'blogs'
    id = StringField(primary_key=True,default = get_id,updatable=False)
    user_id = StringField(updatable=False)
    user_name = StringField()
    name = StringField()
    summary = StringField()
    content = TextField()
    created_at = FloatField(updatable=False,default = time.time)

class Comment(Model):
    __talbe__ = 'comments'
    id = StringField(primary_key = True,default = get_id,updatable=False)
    blog_id = StringField(updatable=False)
    user_id = StringField(updatable=False)
    user_name = StringField()
    content = TextField()   
    created_at = FloatField(updatable=False,default = time.time)

def generate_tables():
    if not db.engine:
        db.create_engine('awesome.db')
    
    sql = lambda x:''.join(x().__sql__.split('\n')[1:])   
    db.update(sql(User))
    db.update(sql(Blog))
    db.update(sql(Comment))

if __name__ == '__main__':
    generate_tables()
    


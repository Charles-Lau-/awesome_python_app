#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest,orm,db

class User(orm.Model):
    id = orm.StringField(default=db.get_id(),primary_key=True,updatable=False) 
    username = orm.StringField(default='admin')
    age = orm.IntegerField(default=10)
    height = orm.FloatField(default=1.2)
    male = orm.BooleanField(default=True)
    
    def pre_insert(self):
        print '========pre========insert'

    def pre_update(self):
        print '--------pre--------update'

    def pre_delete(self):
        print '........pre<<<<<<<<<delete'
    
class TestOrm(unittest.TestCase):
    
    def test_object_creation(self):
        user1 = User(username='John',male=False,height=1.33)

        self.assertEquals(user1.username,'John')
        self.assertEquals(user1.age,10)
        self.assertEquals(user1.height,1.33)
        self.assertEquals(user1.male,False)

        user2 = User()

        self.assertEquals(user2.username,'admin')
        self.assertEquals(user2.age,10)
        self.assertEquals(user2.height,1.3)
        self.assertEquals(user2.male,True)


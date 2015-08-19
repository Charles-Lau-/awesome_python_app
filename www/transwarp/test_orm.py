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
    def setUp(self):
        if not db.engine:
            db.create_engine('test.db')  
        db.update('drop table if exists user')
        create_table_sql =  ''.join(User().__sql__.split('\n')[1:])       
        db.update(create_table_sql)
   
    def tearDown(self):
        pass

    def test_object_creation(self):
        user1 = User(username='John',male=False,height=1.33)

        self.assertEquals(user1.username,'John')
        self.assertEquals(user1.age,10)
        self.assertEquals(user1.height,1.33)
        self.assertEquals(user1.male,False)

        user2 = User()

        self.assertEquals(user2.username,'admin')
        self.assertEquals(user2.age,10)
        self.assertEquals(user2.height,1.2)
        self.assertEquals(user2.male,True)

    def test_object_operations(self):
        #object creation
        user1 = User(username = 'John',male=False,height=1.33)
        user1.insert()
        
        _user1 = User.find_one('where username=?','John')
        self.assertEquals(_user1.height,user1.height)

        #object selection
        _user2 = User.find_all()
        self.assertIsInstance(_user2,list)
        self.assertEquals(len(_user2),1)

        num = User.count_all()
        self.assertEquals(num,1)

        num2 = User.count_by('where username=?','John')
        self.assertEquals(num2,1)

        #object update
        user2 = User(id=user1.id,username='Hanke',male=True,height=12)
        user2.update()

        self.assertEquals(user2.id,user1.id)
        self.assertEquals(user2.username,'Hanke')
        self.assertEquals(user2.male,True)
        self.assertEquals(user2.height,12)

        __user2 = User.get(user1.id)
        self.assertEquals(__user2.username,'Hanke')

        #object deletion
        user2.delete()
        result = User.get(user1.id)
        self.assertIsNone(result)
        self.assertEquals(0,User.count_all())
        

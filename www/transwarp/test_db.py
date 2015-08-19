#!/usr/bin/env python
import unittest
import db

class TestDb(unittest.TestCase):
    def test_dict(self):
        d = db.Dict(('a','b','c'),(1,2,3))

        self.assertEquals(d.a,1)
        self.assertEquals(d.b,2)
        self.assertTrue(isinstance(d,dict))
        self.assertTrue('a' in d)
        self.assertTrue('b' in d)
        
        #test set attribute
        d.a = 4
        self.assertEquals(d.a,4)
        #test exception error

        with self.assertRaises(KeyError):
            value = d['empty']


        with self.assertRaises(AttributeError):
            value = d.empty

    def test_engine(self):
        #check the initial value of engine
        self.assertIsNone(db.engine)
        #initial engine
        db.create_engine('test.db')
        with self.assertRaises(db.DBError):
            db.create_engine('test.db')
        
        #test initialization of _db_ctx object
        self.assertFalse(db._db_ctx.is_init())
        db._db_ctx.init()
        self.assertTrue(db._db_ctx.is_init())
        #test cursor
        self.assertIsNotNone(db._db_ctx.cursor())
        #test cleanup
        db._db_ctx.cleanup()
        self.assertFalse(db._db_ctx.is_init())
      
        
    def test_database_operations(self):
        #initialization of engine
        db.create_engine('test.db')
        #create Table
        db.update('drop table if exists User')
        db.update('create table User(id int primary key, name varchar(20),password varchar(20),gender varchar(8))')
        #insert
        r1 = db.insert('User',id=db.get_id(),name='user1',password='I do not know',gender='male')
        r2 = db.insert('User',id=db.get_id(),name='user2',password='I do either',gender='female')
        r3 = db.insert('User',id=db.get_id(),name='user3',password='I do ssx',gender='male')
        self.assertEquals(r1,1)
        self.assertEquals(r2,1)
        self.assertEquals(r3,1)

        
        #test select
        r4 = db.select_one('select name from User where gender=?','male')
        r5 = db.select_all('select name from User where gender=?','male')

        self.assertIsInstance(r4,dict)
        self.assertIsInstance(r5,list)
        
        r6 = db.select_one('select name from User where gender=?','asldfkj')
        r7 = db.select_all('select name from User where gender=?','asldfkj')

        self.assertIsNone(r6)
        self.assertEquals(r7,[])
        
        #test update
        r8 = db.update('update User SET gender=? where name=?','male','user1')
        r9 = db.update('update User SET gender=? where name=?','male','asdfas')
        r10 = db.update('update User SET name =? where gender=?','haha','male')

        self.assertEquals(r8,1)
        self.assertEquals(r9,0)
        self.assertEquals(r10,2)
    
        #test transactions
        with db.transaction():
            db.insert('User',id=db.get_id(),name='user5',password='asdfa',gender='female')
            db.insert('User',id=db.get_id(),name='user5',password='asdfa',gender='male')

        r12 = db.select_all('select * from User where name=?','user5')
        self.assertEquals(len(r12),2)
        
        db.engine = None

#!/usr/bin/env python
#-*- coding:utf-8 -*-
import time,uuid,functools,threading

#Dict object
class Dict(dict):
    """
    Simple dict object, but allow access like x.y

    """
    def __init__(self,names=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        for k,v in zip(names,values):
            self[k] = v
            
    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r'Dict object has no attribute %s' % key)

    def __setattr__(self,key,value):
        self[key] = value

def get_id(t=None):
    """
    Return unique id which is combination of uuid and timestamp, default timestamp
    is None

    """
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t*1000), uuid.uuid4().hex)
    
class DBError(Exception):
    pass

class MultiColumnError(DBError):
    pass

class _LazyConnection(object):
    """
    Class performs actual connecton, cursor and commit operations

    """
    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            self.connection = engine.connect()
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            self.connection.close()
            self.connection = None

class _DbCtx(threading.local):
    """
   
    Thread local object that holds _Lazyconnection object and the counter of
    transactions

    """
    def __init__(self):
        self.connection = None
        self.transactions = 0
    
    def is_init(self):
        return not self.connection is None

    def init(self):
        self.connection = _LazyConnection()
        self.transactions = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        return self.connection.cursor()
      
# new a threading secure object _db_ctx
_db_ctx = _DbCtx()

#global object engine
engine = None
class _Engine(object):
    def __init__(self,connect):
        self._connect = connect

    def connect(self):
        return self._connect()

def create_engine(database):
    import sqlite3
    global engine
    if engine is not None:
        raise DBError('Engine is already initialized')

    engine = _Engine(lambda : sqlite3.connect(database))

class _ConnectionCtx(object):
    """
    This object is used to support connection context and the with syntax
    
    Usage is like:
        with connection():
            pass
            with connection():
                pass

    """
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
        return self
    
    def __exit__(self,exctype,excvalue,traceback):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()

def connection():
    """
    Return _ConnectionCtx object

    """
    return _ConnectionCtx()

def with_connection(func):
    """
    Decorator for connection
    
    """
    @functools.wraps(func)
    def _wrapper(*args,**kwargs):
        with _ConnectionCtx():
            return func(*args,**kwargs)
    return _wrapper

class _TransactionCtx(object):
    """
    Transaction object that can handle transactions

    with _TransactionCtx():
        pass

    """
    def __enter__(self):
        global _db_ctx
        self.should_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_close_conn = True
        _db_ctx.transactions = _db_ctx.transactions + 1
        return self
        
    def __exit__(self,exctype,excvalue,traceback):
        global _db_ctx
        _db_ctx.transactions = _db_ctx.transactions -1
        try:
            if _db_ctx.transactions == 0:
                if exctype is None:
                    self.commit()
                else:
                    self.rollback()
        finally:
            if self.should_close_conn:
                _db_ctx.cleanup()

    def commit(self):
        global _db_ctx
        try:
            _db_ctx.connection.commit()
        except:
            _db_ctx.connection.rollback()
            raise

    def rollback(self):
        global _db_ctx
        _db_ctx.connection.rollback()

def transaction():
    """
    Create a transaction object

    """
    return _TransactionCtx()

def with_transaction(func):
    """
     Transaction decorator

    """
    @functools.wraps(func)
    def _wrapper(*args,**kw):
        with _TransactionCtx():
            return func(*args,**kw)
    return _wrapper
    
def _select(sql,first,*args):
    """
    Execute sql statement and return result list or one result

    """
    global _db_ctx
    cursor = None
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql,args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names,values)
        return [Dict(names,x) for x in cursor.fetchall()]

    finally:
        
        if cursor:
            cursor.close()

@with_connection
def select_one(sql,*args):
    """
    Return the first found result or None
    
    """
    return _select(sql,True,*args)

@with_connection
def select_all(sql,*args):
    """
    Execute select SQL and return list or empty list if no result
    
    """
    return _select(sql,False,*args)
    
@with_connection
def _update(sql,*args):
    global _db_ctx
    cursor = None
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql,args)
        r = cursor.rowcount
        if _db_ctx.transactions == 0:
            _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()

def update(sql,*args):
    
    return _update(sql,*args)
    
def insert(table,**kw):
    cols,args = zip(*kw.iteritems())
    
    sql = 'insert into `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % col for  col in cols]), ','.join(['?' for i in range(len(cols))]))  

    return _update(sql,*args)

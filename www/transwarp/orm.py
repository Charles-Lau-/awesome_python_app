#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
ORM operations module
"""
import db

class Field(object):
    _count = 0
    def __init__(self,**kw):
        self.name = kw.get('name',None)
        self._default = kw.get('default',None)
        self.primary_key = kw.get('primary_key',False)
        self.nullable = kw.get('nullable',False)
        self.updatable = kw.get('updatable',True)
        self.insertable = kw.get('insertable',True)
        self.ddl = kw.get('ddl','')
        #_order is used to sort added Field, so that they can be shown in the order
        # that they are added
        self._order = Field._count
        Field._count = Field._count + 1

    @property
    def default(self):
        d = self._default
        return d() if callable(d) else d
     
    def __str__(self):
        s = ['<%s:%s,%s,default(%s),' % (self.__class__.__name__,self.name,self.ddl,self._default)]
        self.nullable and s.append('N')
        self.updatable and s.append('U')
        self.insertable and s.append('I')
        s.append('>')
        return ''.join(s)
        
class StringField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'varchar(255)'
        super(StringField,self).__init__(**kw)

class IntegerField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = 0

        if not 'ddl' in kw:
            kw['ddl'] = 'bigint'

        super(IntegerField,self).__init__(**kw)

class FloatField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = 0.0
        if not 'ddl' in kw:
            kw['ddl'] = 'real'
        super(FloatField,self).__init__(**kw)

class BooleanField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = False
        if not 'ddl' in kw:
            kw['ddl'] = 'bool'
        super(BooleanField,self).__init__(**kw)

class TextField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = ''
        if not 'ddl' in kw:
            kw['ddl'] = 'text'
        super(TextField,self).__init__(**kw)

class BlobField(Field):
    def __init__(self,**kw):
        if not 'default' in kw:
            kw['default'] = '' 
        if not 'ddl' in kw:
            kw['ddl'] - 'blob'
        super(BlobField,self).__init(**kw)

class VersionField(Field):
    def __init__(self,name=None):
        super(VersionField,self).__init__(name=name,default=0,ddl='bigint')

#triggers sending signals before some specific operations
_triggers = frozenset(['pre_update','pre_insert','pre_delete'])

class ModelMetaclass(type):
    """
    Metaclass for Model

    """
    def __new__(cls,name,bases,attrs):
        if name == 'Model':
            return type.__new__(cls,name,bases,attrs)
        #store all subclasses info
        if not hasattr(cls,'subclasses'):
            cls.subclasses = {}
        if not name in cls.subclasses:
            cls.subclasses[name] = name

        mappings = {}
        primary_key = None
        for k,v in attrs.iteritems():
            if isinstance(v,Field):
                #if data table column name does not set, then set it as same as attribute
                if not v.name:
                    v.name = k
            #check duplicate primary key    
                if v.primary_key:
                    if primary_key:
                        raise TypeError("Can not define two primary key")
                    if v.updatable:
                        raise TypeError("Primary key can not be set as updatable")
                    if v.nullable:
                        raise TypeError("Primary key can not be set as nullable")
                    primary_key = v
                mappings[k] = v
        #check existence of primary key
        if not primary_key:
            raise TypeError("Primary key is not set")

        #remove Field part from class attributes
        for k in mappings.keys():
            attrs.pop(k)
        if not '__table__' in attrs:
            attrs['__table__']  =  name.lower()
        attrs['__mappings__'] =  mappings
        attrs['__primary_key__'] = primary_key
        attrs['__sql__'] = _create_table(attrs['__table__'],mappings)
        #add trigger methods 
        for t in _triggers:
            if not t in attrs:
                attrs[t] = None
        return type.__new__(cls,name,bases,attrs)
 
class Model(dict):
   """
    Base class for ORM
    Userful operation methods are defined in this class, and property accessibility is
    enabled in the definition of this class
   """
   __metaclass__ = ModelMetaclass
   def __init__ (self,**kw):
        super(Model,self).__init__(**kw)
        for k,v in self.__mappings__.iteritems():
            if not hasattr(self,k):
                setattr(self,k,v.default)

   def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"`Dict` object has no attribute %s" % key)

   def __setattr__(self,key,value):
        self[key] = value

   @classmethod
   def get(cls,pk):
        """
        Get by primary key
        """
        d = db.select_one('select * from %s where %s=?' % (cls.__table__,
                          cls.__primary_key__.name),pk)
        return cls(**d) if d else None
   @classmethod
   def find_one(cls,where,*args):
        """
         Find the one suject to the where clause
        """
        d = db.select_one('select * from %s %s' % (cls.__table__,where), *args)
        return cls(**d) if d else None

   @classmethod
   def find_all(cls):
        """
        Find all and return list
        """
        d = db.select_all('select * from `%s`' % cls.__table__)
        return [cls(**l) for l in d]

   @classmethod
   def find_by(cls,where,*args):
        """
        Find by where clause and return list
        """
        L =  db.select_all('select * from `%s` %s' % (cls.__table__,where), *args)
        return [cls(**t) for t in L]

   @classmethod
   def count_all(cls):
        """
        Find by 'select count(pk) from table' and return integer
        """
        return len(cls.find_all())

   @classmethod
   def count_by(cls,where,*args):
        """
        Find by 'select count(pk) from table where ...

        """
        return len(cls.find_by(where,*args))
    
   def update(self):
        self.pre_update and self.pre_update()
        L = []
        args = []
        for k,v in self.__mappings__.iteritems():
            if v.updatable:
                arg = getattr(self,k)
                L.append('`%s`=?' % k)
                args.append(arg)
        pk = self.__primary_key__.name
        args.append(getattr(self,pk))
        db.update('update `%s` set %s where %s=?' % (self.__table__,','.join(L),pk),*args)
        return self

   def delete(self):
        self.pre_delete and self.pre_delete()
        pk = self.__primary_key__.name
        args = (getattr(self,pk),)
        db.update('delete from `%s` where `%s`=?' % (self.__table__,pk),*args)
        return self

   def insert(self):
        self.pre_insert and self.pre_insert()
        params = {}
        for k,v in self.__mappings__.iteritems():
            if v.insertable:
                params[v.name] = getattr(self,k)
        db.insert('%s' % self.__table__,**params) 
        return self

def _create_table(table_name,mappings):
    pk = None
    sql = ['--generating SQL for %s:' % table_name,'create table `%s` (' % table_name]
    for f in sorted(mappings.values(),lambda x,y: cmp(x._order,y._order)):
        if not hasattr(f,'ddl'):
            raise StandardError('no ddl in field `%s`' % f)
        ddl = f.ddl
        nullable = f.nullable
        if f.primary_key:
            pk = f.name
        sql.append(nullable and '`%s` %s,' % (f.name,ddl) 
                        or'`%s` %s not null,' % (f.name,ddl)) 
    sql.append(' primary key(`%s`)' % pk)
    sql.append(');')
    return '\n'.join(sql)

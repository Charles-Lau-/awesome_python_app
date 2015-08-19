#!/usr/bin/env python

class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if not name == 'Model':
            attrs['new_function'] = lambda x:  'hahah'

        return type.__new__(cls,name,bases,attrs)
 
class Model(dict):
    __metaclass__ = ModelMetaclass

    def __init__ (self,**kw):
        super(Model,self).__init__(**kw)

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"`Dict` object has no attribute %s" % key)

    def __setattr__(self,key,value):
        self[key] = value


class User(Model):
    a = 'a'
 
if __name__ == '__main__':
    print User().new_function()

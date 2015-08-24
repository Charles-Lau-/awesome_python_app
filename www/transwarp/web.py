#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
A simple, lightweight, WSGI-compatible web framework

"""
import types, os, re, cgi, sys, time, datetime, functools, mimetypes, threading, logging
import urllib,traceback

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

#threading local object for storing request and response object
ctx = threading.local()

_TIMEDELTA_ZERO = datetime.timedelta(0)

_RE_TZ = re.compile('^([\+\-])([0-9]{1,2})\:([0-9]{1,2})$')

class UTC(datetime.tzinfo()):
    """
    A UTC time info class

    Usage:
        tz0 = UTC('+9:39')
        tz0.tzname(None)
        'UTC+9:39'
    """
    def __init__(self,utc):
        utc = str(utc.strip().upper())
        mt = _RE_TZ.match(utc)
        if mt:
            minus = mt.group(1) == '-'
            h = int(mt.group(2))
            m = int(mt.group(3))
            if minus:
                h,m = (-h),(-m)
            self._utcoffset = datetime.timedelta(hours=h,minutes=m)
            self._tzname = 'UTC%s' % utc
        else:
            raise ValueError('bad utc time format')


    def utcoffset(self):
        return self._utcoffset
    def tzname(self):
        return self._tzname
    def __unicode__(self):
        return 'UTC object (%s) ' % self._tzname

    __repr__ = __unicode__
        
#All known http response
_RESPONSE_STATUSES = {
   100:'Continue', 
   101:'Switching Protocol',
   102:'Processing',
    
   200:'OK', 
   201:'Created', 
   202:'Accepted', 
   203:'Non-Authoritative Information', 
   204:'No Content',
   205:'Reset Content',
   206:'Partial Content',
   207:'Multi Status',
   226:'IM used',

   300:'Multiple Choices',
   301:'Moved Permanently',
   302:'Found',
   303:'See Other',
   304:'Not Modified',
   305:'Use Proxy',
   307:'Temporary Redirected',
   
   400:'Bad Request',
   401:'Unauthorized',
   402:'Payment Required',
   403:'Forbidden',
   404:'Not Found',
   405:'Method Not Allowed',
   406:'Not Acceptable',
   407:'Proxy Authentication Required',
   408:'Request Timeout',
   409:'Conflict',
   410:'Gone',
   411:'Length Required',
   412:'Precondition Failed',
   413:'Request Entity Too Large',
   414:'Request URI Too Long',
   415:'Unsupported Media Type',
   416:'Request Range Not Satisfiable',
   417:'Expectation Failed',
   418:'I\'m a teapot',
   419:'Unprocessable Entity',
   420:'Locked',
   421:'Failed Dependency',
   422:'Upgrade Required', 
    
   #Server Error
   500:'Internal Server Error',
   501:'Not Implemented',
   502:'Bad Gateway',
   503:'Service Unavailable',
   504:'Gateway Timeout',
   505:'HTTP Version not Suppoted',
   507:'Insufficient Storage',
   510:'Not Extended'

}

_RE_RESPONSE_STATUS = re.compile(r'^\d\d\d(\[\w\]+)?$')

_RESPONSE_HEADERS = (
    'Accept-Ranges',
    'Age',
    'Allow',
    'Cache-Control',
    'Connection',
    'Content-Encoding',
    'Content-Language',
    'Content-Length',
    'Content-Location',
    'Content-MD5',
    'Content-Disposition',
    'Content-Range',
    'Content-Type',
    'Date',
    'ETag',
    'Expires',
    'Last-Modified',
    'Link',
    'Location',
    'P3P',
    'Pragma',
    'Proxy-Authenticate',
    'Refresh',
    'Retry-After',
    'Server',
    'Set-Cookie',
    'Strict-Transport-Security',
    'Trailer',
    'Transfer-Encoding',
    'Vary',
    'Via',
    'Warning',
    'WWW-Authenticate',
    'X-Frame-Options',
    'X-XSS-Protection',
    'X-Content-Type-Options',
    'X-Forwarded-Proto',
    'X-Powered-By',
    'X-UA-Compatible'
)

_RESPONSE_HEADER_DICT = dict(zip(map(lambda x:x.upper(),_RESPONSE_HEADERS),_RESPONSE_HEADERS))
        
_HEADER_X_POWERED_BY = ('X-Powered-By','transwarp/1.0')

class HttpError(Exception):
    """
    Base HttpError class which  defines http error code

    Usage:
        e = HttpError(404)
        e.status
        '404 Not Found
    """

    def __init__(self,code):
        """
        Init HttpError with an error code

        """
        super(HttpError,self).__init__()
        self.status = '%d %s' % (code, _RESPONSE_STATUSES[code])

    def add_header(self,name,value):
        if not hasattr(self,'_headers'):
           self._headers = [_HEADER_X_POWERED_BY]
        self._headers.append((name,value))

    @property
    def headers(self):
        if hasattr(self,'_headers'):
            return self._headers
        return []

    def __unicode__(self):
        return self.status
    __repr__ == __unicode__

class RedirectError(HttpError):
    def __init__(self,code,location):
        super(RedirectError,self).__init__(code)
        self.location = location
    
    def __unicode__(self):
        return "%s,%s" % (self.status,self.location)
    
    __repr__ = __unicode__

    
def bad_request():
    return HttpError(404)

def unauthorized():
    return HttpError(401)

def forbidden():
    return HttpError(403)

def notfound():
    return HttpError(404)

def conflict():
    return HttpError(409)

def internalerror():
    return HttpError(500)

def redirect(location):
    return RedirectError(301,location)

def found(location):
    return RedirectError(302,location)

def seeother(location):
    return RedirectError(303,location)

def _to_strs(s):
    if isinstance(s,str):
        return s
    if isinstance(s,unicode):
        return s.encode('utf-8')
    return str(s)

def _to_unicode(s):
    return s.decode('utf-8')

def _quote(s):
    if isinstance(s,unicode):
        s = s.encode('utf-8')
    return urllib.quote(s)

def _unquote(s,encoding='utf-8'):
   return urllib.unquote(s).decode(encoding)

_re_route = re.compile(r'(\:[a-zA-Z_]\w*)')

def _build_regex(path):
    r'''
    Convert route path to regex.
    >>> _build_regex('/path/to/:file')
    '^\\/path\\/to\\/(?P<file>[^\\/]+)$'
    >>> _build_regex('/:user/:comments/list')
    '^\\/(?P<user>[^\\/]+)\\/(?P<comments>[^\\/]+)\\/list$'
    >>> _build_regex(':id-:pid/:w')
    '^(?P<id>[^\\/]+)\\-(?P<pid>[^\\/]+)\\/(?P<w>[^\\/]+)$'
    '''
    re_list = ['^']
    var_list = []
    is_var = False
    for v in _re_route.split(path):
        if is_var:
            var_name = v[1:]
            var_list.append(var_name)
            re_list.append(r'(?P<%s>[^\/]+)' % var_name)
        else:
            s = ''
            for ch in v:
                if ch>='0' and ch<='9':
                    s = s + ch
                elif ch>='A' and ch<='Z':
                    s = s + ch
                elif ch>='a' and ch<='z':
                    s = s + ch
                else:
                    s = s + '\\' + ch
            re_list.append(s)
        is_var = not is_var
    re_list.append('$')
    return ''.join(re_list)

class Route(object):
    """
    A Route object is callable
    
    """
    def __init__(self,func):
        self.path = func.__web_route__
        self.method = func.__web_method__
        self.is_static = _re_route.search(self.path) is None
        if not self.is_static:
            self.route = re.compile(_build_regex(self.path))
        self.func = func

    def match(self,url):
        m = self.route.match(url)
        if m:
            return m.groups()
        return None

    def __call__(self,*args):
        return self.func(*args)

    def __unicode__(self):
        if self.is_static:
            return 'Route Static %s , path = %s' % (self.method,self.path)
        return 'Route dynamic %s , path = %s' % (self.method,self.path)

    __repr__ = __unicode__

def _static_file_generator(fpath):
    BLOCK_SIZE = 8192
    with open(fpath,'rb') as f:
        block = f.read(BLOCK_SIZE)
        while block:
            yield block
            block = f.read(BLOCK_SIZE)

class StaticFileRoute(object):
    def __init__(self):
        self.method = 'GET'
        self.is_static = False
        self.route = re.compile('^/static/(.+)$')

    def match(self,url):
        if url.startswith('/static/'):
            return (url[1:],)
        return None

    

    

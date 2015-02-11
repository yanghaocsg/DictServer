#!/usr/bin/env python
#coding: utf8
import sys, re, logging, redis,traceback, time, os, simplejson, datetime
from multiprocessing import Pool, Queue
from collections import defaultdict
from bson.binary import Binary
import string
from unipath import Path
import cPickle, lz4
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.gen, tornado.web
import logging, ConfigParser

#self module
import YhLog, DictConf
logger = logging.getLogger(__file__)

class root_handler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        try:
            dict_res=dict()
            self.write('ok')
        except Exception as e:
            logger.error('root handler fail')
            self.write('<Html><Body>Server fail:'+str(e)+'</Body></Html>')
        finally:
            try:
                self.finish()
            except:
                pass
                
def multi_app():
    settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "../static"),
    #"cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    #"login_url": "/login",
    #"xsrf_cookies": True,
    }   
    cwd = Path(__file__).absolute().ancestor(1)
    config = ConfigParser.ConfigParser()
    #config.read(Path(cwd, './conf/backend.conf'))
    port = 8889
    app = tornado.web.Application(handlers=[
        (r'/', root_handler),
        (r'/favicon.ico', root_handler),
        (r'/reload', DictConf.Reload_handler),
        (r'/se', DictConf.Search_Handler),
        ], **settings)
    http_server = HTTPServer(app)
    http_server.bind(port)
    http_server.start()
    logger.error('listen port %s' % port)
    IOLoop.instance().start()
    
        
        
if __name__ == '__main__':
    '''pid = os.fork()
    if(pid >0):
        os._exit(0)
    '''
    multi_app()
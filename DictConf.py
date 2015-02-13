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
import ConfigParser
import eventlet
import threading, glob

#self module
import YhLog, YhTool
logger = logging.getLogger(__file__)

class DictManager:
    def __init__(self, conf='./conf/dict.conf'):
        self.cwd = Path(__file__).absolute().ancestor(1)
        self.conf = conf
        self.dict_manager = {}
        self.load()
        
    def load(self):
        self.config=ConfigParser.ConfigParser({'type':'unigram', 'fn_txt':'', 'fn_pic':''})
        self.config.read(Path(self.cwd, self.conf))
        for sec in self.config.sections():
            dict_type = self.config.get(sec, 'type')
            txt = self.config.get(sec, 'fn_txt')
            pic = self.config.get(sec, 'fn_pic')
            self.dict_manager[sec] = self.load_dict(dict_type, txt, pic)
            logger.error('init name %s len %s type %s data %s' % (sec, len(self.dict_manager[sec]), self.config.get(sec, 'type'), self.dict_manager[sec].items()[:3]))
            
    def load_dict(self, dict_type='unigram', fn_txt='', fn_pic=''):
        if dict_type not in ['unigram', 'bigram']:
            raise Exception('dict type error')
        dict_tmp = {}
        if fn_pic:
            for f in glob.glob(Path(self.cwd, fn_pic)):
                d = cPickle.load(open(f))
                dict_tmp.update(d)
                logger.error('load_dict %s %s %s' % (f, len(d), len(dict_tmp)))
        else:
            for f in glob.glob(Path(self.cwd, fn_txt)):
                d = {}
                for l in open(f):
                    l = unicode(l.strip(), 'utf8', 'ignore')
                    if not l: continue
                    if dict_type == 'bigram':
                        k, v = re.split('\t', l, 2)
                        v = int(v)
                        if k and v:
                            d[k] = v
                    else:
                        d[l] = 1
                dict_tmp.update(d)
                logger.error('load_dict %s %s %s' % (f, len(d), len(dict_tmp)))
        return dict_tmp
        
    def get_query(self, req={}):
        name = req.get('dict', '')
        query = req.get('query', '')
        dict_res = {}
        logger.error('get_query %s\t%s\t%s' % (name, query, name in self.dict_manager))
        if name and query and name in self.dict_manager:
            try:
                if isinstance(query, list):
                    for q in query:
                        val = self.dict_manager[name].get(q,0)
                        if val:
                            dict_res[q] = val
                        else:
                            logger.error('not found %s' % q)
                            
                else:
                    val = self.dict_manager[name].get(query,0)
                    if val:
                        dict_res[query] = val
                    else:
                        logger.error('not found %s' % val)
            except:
                logger.error('DictManager %s' % traceback.format_exc())
        return dict_res


def reload():
    print "reload begin"
    global idx_manager_lock, manager, idx_manager
    logger.error('idx_manager[%s], idx_manager_lock[%s]' % (idx_manager, idx_manager_lock))
    if idx_manager_lock:
        #already reloading
        return 2  
    idx_manager_lock = 1 
    idx_manager_backup = (idx_manager + 1) % 2
    manager[idx_manager_backup] = DictManager()
    manager[idx_manager] = {}
    idx_manager = idx_manager_backup
    
    idx_manager_lock = 0
    print "reload end"
    return idx_manager
    
class Reload_handler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        try:
            logger.error('get request %s' % self.request.uri)
            global idx_manager_lock, idx_manager
            dict_res=dict()
            t = threading.Thread(target=reload)
            t.daemon = True
            t.start()
            self.write({'status':0, 'idx_manager':idx_manager, 'idx_manager_lock':idx_manager_lock})
        except:
            logger.error('reload handler fail')
            self.write({'status':-1, 'res':traceback.format_exc()})
        finally:
            self.finish()
            logger.error('request_time %s [%s]' %(self.request.uri, self.request.request_time()))

class Search_Handler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        try:
            dict_qs = YhTool.yh_urlparse_params(self.request.uri, ['req'], [''])
            query = dict_qs['req']
            dict_req = simplejson.loads(query)
            logger.error(dict_req)
            dict_res = manager[idx_manager].get_query(dict_req)
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(simplejson.dumps(dict_res))
        except:
            logger.error('search handler fail %s' % traceback.format_exc())
            self.write({'status':-1, 'res':traceback.format_exc()})
        finally:
            self.finish()
            logger.error('request_time %s [%s]' %(self.request.uri, self.request.request_time()))
            

manager = [DictManager(), {}]
idx_manager = 0
idx_manager_lock = 0

if __name__=='__main__':
    logger.error('start main')
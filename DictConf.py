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
import threading

#self module
import YhLog, YhTool
logger = logging.getLogger(__file__)

class DictManager:
    def __init__(self, conf='./conf/dict.conf', password=''):
        self.cwd = Path(__file__).absolute().ancestor(1)
        self.config = ConfigParser.ConfigParser()
        self.config.read(Path(self.cwd, conf))
        self.dict_manager = {}
        self.load()
        
    def load(self):
        for sec in self.config.sections():
            dict_tmp = {}
            
            try:
                dict_type = self.config.get(sec, 'type')
                if  dict_type in ['unigram']:
                    logger.error('before load_unigram')
                    dict_tmp = self.load_unigram(self.config.get(sec, 'fn_txt'))
                elif dict_type in ['bigram']:
                    logger.error('before load_bigram')
                    dict_tmp = self.load_bigram(self.config.get(sec, 'fn_txt'))
                else:
                    logger.error('before nochoice')
                logger.error('sec [%s] type [%s]' % (sec, dict_type))
            except:
                logger.error('DictConf error %s' % traceback.format_exc())
            self.dict_manager[sec] = dict_tmp
            logger.error('init name %s len %s type %s' % (sec, len(self.dict_manager[sec]), self.config.get(sec, 'type')))
            
    def load_unigram(self, ifn_txt=''):
        dict_tmp = {}
        for l in open(Path(self.cwd, ifn_txt)):
            l = unicode(l.strip(), 'utf8', 'ignore')
            if not l: continue
            dict_tmp[l] = 1
        logger.error('load_unigram %s %s' % (ifn_txt, len(dict_tmp)))
        return dict_tmp
    
    def load_bigram(self, ifn_txt=''):
        dict_tmp = {}
        for l in open(Path(self.cwd, ifn_txt)):
            try:
                l = unicode(l.strip(), 'utf8', 'ignore')
                if not l: continue
                k,v = l.split('\t')[:2]
                dict_tmp[k] = int(v)
            except:
                #logger.error('load_bigram %s %s' % (l, traceback.format_exc()))
                pass
        logger.error('load_bigram %s %s' % (ifn_txt, len(dict_tmp)))
        return dict_tmp
    
    def get_query(self, req={}):
        name = req.get('dict', '')
        query = req.get('query', '')
        dict_res = {}
        if sec and query and sec in self.dict_manager:
            try:
                if isinstance(query, list):
                    for q in query:
                        val = self.dict_manager[name].get(q,0)
                        if val:
                            dict_res[q] = val
                else:
                    val = self.dict_manager[name].get(query,0)
                    if val:
                        dict_res[query] = val
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
            dict_res = manager[idx_manager].get(dict_req)
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(simplejson.dumps(dict_res))
        except:
            logger.error('search handler fail')
            self.write({'status':-1, 'res':traceback.format_exc()})
        finally:
            self.finish()
            logger.error('request_time %s [%s]' %(self.request.uri, self.request.request_time()))
            

manager = [DictManager(), {}]
idx_manager = 0
idx_manager_lock = 0

if __name__=='__main__':
    logger.error('start main')
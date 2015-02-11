#!/usr/bin/env python
#coding: utf8
import sys, re, logging, redis,traceback, time, os, simplejson, datetime
from multiprocessing import Pool, Queue
from collections import defaultdict
from bson.binary import Binary
import string
from unipath import Path
import cPickle, lz4
import logging, urllib
from eventlet.green import urllib2
#self module
import YhLog
logger = logging.getLogger(__file__)

def test():
    dict_req = {'dict':'keyword', 'query':['abc', '电影', '电视', '二炮手']}
    url_req = 'http://127.0.0.1:8888/se?req=%s' % (urllib.quote_plus(simplejson.dumps(dict_req)))
    logger.error(url_req)
    res = urllib2.urlopen(url_req).read()
    logger.error(simplejson.loads(res))
    
        
        
if __name__ == '__main__':
    test()
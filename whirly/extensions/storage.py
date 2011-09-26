# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Yuanhao Li
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


__all__ = ['StorageEngineError', 'MySQL', 'MongoDB', 'Redis']


import re
import logging

from whirly.extensions.base import Extension


class DatabaseExtension(Extension):
    def __init__(self):
        self.define_required('database_url', 'url to connect database')
        super(DatabaseExtension, self).__init__('database')
        self.db_url = self.settings.get('database_url')
        db_type = self.db_url.split('://')[0].lower()
        logging.debug("Database url selected: %s" % self.db_url)


class StorageEngineError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class StorageEngine(object):
    __state = {}

    def __init__(self, db_url):
        self.__dict__ = self.__state
        self.db_url =  db_url
        self.db_type = db_url.split('://', 1)[0]

    def get_engine(self):
        if self.db_type not in self.__state.keys():
            self.create_engine()
        return self.engine

    @property
    def engine(self):
        logging.debug(self.__state)
        return self.__state[self.db_type]

    @property
    def db(self):
        logging.debug(self.__state)
        return self.__state['%s_db' % self.db_type]

    def _set_engine(self, engine, db=None):
        self.__state[self.db_type] = engine
        if db:
            self.__state['%s_db' % self.db_type] = db

    def create_engine(self):
        pass


class StorageEngineMemcached(StorageEngine):
    """memcached://host, host, host, ...
    """
    def create_engine(self):

        def parse_url(db_url):
            if len(db_url) > 12:
                return re.sub('\s+', '', db_url[12:]).split(',')
            else:
                return ['127.0.0.1']

        try:
            import pylibmc
        except ImportError:
            raise StorageEngineError("Could not find the driver for memcached. ")

        servers = parse_url(self.db_url)
        engine = pylibmc.Client(servers, binary=True)
        engine.behaviours['no_block'] = 1 # async I/O
        self._set_engine(engine)


class StorageEngineMongoDB(StorageEngine):
    """mongodb://[host[:port]]/db
    """
    def create_engine(self):
        def parse_url(db_url):
            match = re.match('mongodb://([\S|\.]+?)?(?::(\d+))?/(\S+)', db_url)
            host = match.group(1)
            port = match.group(2)
            db = match.group(3)

            logging.debug("Host: %s" % host)
            logging.debug("Port: %s" % port)
            logging.debug("Database: %s" % db)

            return host, int(port), db

        try:
            import pymongo
        except ImportError:
            raise StorageEngineError("Could not find the driver for mongodb. ")

        host, port, db = parse_url(self.db_url)
        conn = pymongo.Connection(host=host, port=port)
        self._set_engine(conn, db=conn[db])


class MongoDB(DatabaseExtension):
    def before(self, handler):
        store = StorageEngineMongoDB(self.db_url)
        store.get_engine()
        handler.db = store.db
        return handler


class StorageEngineDatastore(StorageEngine):
    """datastore://google
    """
    def create_engine(self):
        try:
            from google.appengine.ext import db
        except ImportError:
            raise StorageEngineError("Could not find the driver for datastore. ")

        self._set_engine(db)


class StorageEngineMemcache(StorageEngine):
    """memcache://google
    """
    def create_engine(self):
        try:
            from google.appengine.api import memcache
        except ImportError:
            raise StorageEngineError("Could not find the driver for googe "
                                "appengine memcache. ")
        self._set_engine(memcache)


class StorageEngineRedis(StorageEngine):
    """redis://[auth@][host[:port]][/db]
    """
    def create_engine(self):

        def parse_url(db_url):
            match = re.match('redis://(?:(\S+)@)?([^\s:/]+)?(?::(\d+))?(?:/(\d+))?$', db_url)
            pwd, host, port, db = match.groups()

            logging.debug("Password: %s" % pwd)
            logging.debug("Host: %s:%s" % (host, port))
            logging.debug("Database: %s" % db)

            return pwd, host, int(port), int(db)

        try:
            import redis
        except ImportError:
            raise StorageEngineError("Could not find driver for redis. ")

        pwd, host, port, db = parse_url(self.db_url)
        engine = redis.Redis(host=host, port=port, db=db, password=pwd)
        self._set_engine(engine)


class Redis(DatabaseExtension):
    def before(self, handler):
        handler.db = StorageEngineRedis(self.db_url).get_engine()
        return handler


class StorageEngineMySQL(StorageEngine):
    """mysql://username:password[@hostname[:port]]/db
    """
    def create_engine(self):
        def parse_url(db_url):
            if db_url.find('@') != -1:
                match = re.match('mysql://(\w+):(.*?)@([\w|\.]+)(?::(\d+))?/(\S+)', db_url)
                username = match.group(1)
                password = match.group(2)
                hostname = match.group(3)
                port = match.group(4) or '3306'
                database = match.group(5)
                host = hostname + ':' + port
            else: # hostname and port not specified
                host = 'localhost:3306'
                match = re.match('mysql://(\w+):(.*?)/(\S+)', db_url)
                username = match.group(1)
                password = match.group(2)
                database = match.group(3)
            logging.debug("Username: %s" % username)
            logging.debug("Password: %s" % password)
            logging.debug("Host: %s" % host)
            logging.debug("Database: %s" % database)
            return username, password, host, database

        try:
            from tornado import database as mysql
        except ImportError:
            raise StorageEngineError("Could not find driver for mysql. ")

        user, pwd, host, db = parse_url(self.db_url)
        self._set_engine(mysql.Connection(host, db, user=user, password=pwd))


class MySQL(DatabaseExtension):
    def before(self, handler):
        handler.db = StorageEngineMySQL(self.db_url).get_engine()
        return handler


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


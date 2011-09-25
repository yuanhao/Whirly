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


__all__ = ['SessionStoreDelegate']


import os
import base64
import re
import logging
import time
import datetime
import hashlib

try:
    import cPickle as pickle
except:
    import pickle

try:
    import redis
except ImportError:
    pass

# try:
    # import pymongo
# except ImportError:
    # pass

try:
    from google.appengine.ext import db as datastore

    class WhirlySession(datastore.Model):
        session_id = datastore.StringProperty(required=True, indexed=True)
        atime = datastore.DateTimeProperty(auto_now_add=True)
        data = datastore.TextProperty()

except ImportError:
    pass

try:
    from MySQLdb import ProgrammingError
except ImportError:
    pass


import whirly.project
import whirly.utils
from whirly.extensions.storage import StorageEngineMongoDB
from whirly.extensions.storage import StorageEngineMySQL
from whirly.extensions.storage import StorageEngineRedis
from whirly.extensions.storage import StorageEngineError


_log = logging.getLogger('whirly.extensions.session.store')


RELATION_DB_SQL_CREATE_TABLE = """
CREATE TABLE whirly_sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
)
"""

RELATION_DB_SQL_QUERY_SESSION = """
    SELECT * FROM whirly_sessions WHERE session_id=%s
"""

RELATION_DB_SQL_UPDATE_SESSION_ATIME = """
    UPDATE whirly_sessions SET atime=%s WHERE session_id=%s
"""

RELATION_DB_SQL_UPDATE_SESSION_DATA = """
    UPDATE whirly_sessions SET data=%s, atime=%s WHERE session_id=%s
"""

RELATION_DB_SQL_INSERT_SESSION = """
    INSERT INTO whirly_sessions (session_id, data)
    VALUES (%s, %s)
"""

RELATION_DB_SQL_DELETE_SESSION = """
    DELETE FROM whirly_sessions WHERE session_id=%s
"""

RELATION_DB_SQL_CLEANUP_SESSION = """
    DELETE FROM whirly_sessions WHERE atime<%s
"""


class SessionStoreError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class SessionStore(object):
    def __init__(self, storage_url='dir://'):
        self.storage_url = storage_url

    def __contains__(self, key):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def cleanup(self, timeout):
        raise NotImplementedError

    @staticmethod
    def encode(session_dict):
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    @staticmethod
    def decode(session_data):
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)


class SessionStoreDirectory(SessionStore):
    """ dir://path/to/storage/dir
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreDirectory, self).__init__(storage_url=storage_url)
        url_re = re.compile(r"dir://(.*)")
        match = url_re.match(self.storage_url)
        _path = match.groups()[0]
        if not os.path.exists(_path):
            _path = whirly.project.project_directory()
        self.path = os.path.join(_path, 'data')
        self.path = os.path.join(self.path, 'sessions')

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        _log.debug('Session store path: %s' % self.path)

    def _get_path(self, key):
        if os.path.sep in key:
            raise SessionStoreError("Bad key %s" % key)
        path = hashlib.md5(key.encode('utf-8')).hexdigest()
        path = os.path.join(path[:2], path[2:4], path[4:])
        return os.path.join(self.path, path)
        #return os.path.join(self.path, key)

    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            raise SessionStoreError("Key does not exist: %s" % key)

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)
        try:
            f = open(path, 'w')
            try:
                f.write(pickled)
            finally:
                f.close()
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)

        if os.path.exists(path):
            os.remove(path)

        try:
            dirname = os.path.dirname(path)
            os.rmdir(dirname)
            os.rmdir(os.path.dirname(dirname))
        except (IOError, OSError):
            pass

    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.path):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout:
                os.remove(path)


class SessionStoreMySQL(SessionStore):
    """ Session storage in MySQL database.
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreMySQL, self).__init__(storage_url=storage_url)
        try:
            self.engine = StorageEngineMySQL(self.storage_url).get_engine()
        except StorageEngineError:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)

    def __contains__(self, key):
        k = whirly.utils.sqlify(key)
        data = self.engine.query(RELATION_DB_SQL_QUERY_SESSION % k)
        return bool(data)

    def __getitem__(self, key):
        now = whirly.utils.sqlify(datetime.datetime.utcnow())
        k = whirly.utils.sqlify(key)
        try:
            s = self.engine.query(RELATION_DB_SQL_QUERY_SESSION % k)[0]
            self.engine.execute(RELATION_DB_SQL_UPDATE_SESSION_ATIME % (now, k))
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        p = whirly.utils.sqlify(pickled) #XXX should sqlify???
        k = whirly.utils.sqlify(key) #XXX should sqlify???
        now = whirly.utils.sqlify(datetime.datetime.utcnow())

        if key in self:
            self.engine.execute(RELATION_DB_SQL_UPDATE_SESSION_DATA % (p, now, k))
        else:
            self.engine.execute(RELATION_DB_SQL_INSERT_SESSION % (k, p))

    def __delitem__(self, key):
        k = whirly.utils.sqlify(key)
        self.engine.execute(RELATION_DB_SQL_DELETE_SESSION % k)

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60))
        last_allowed_time = datetime.datetime.utcnow() - timeout
        l = whirly.utils.sqlify(last_allowed_time)
        try:
            self.engine.execute(RELATION_DB_SQL_CLEANUP_SESSION % l)
        except ProgrammingError, e:
            if e[0] == 1146:
                self.engine.execute(RELATION_DB_SQL_CREATE_TABLE)
            self.engine.execute(RELATION_DB_SQL_CLEANUP_SESSION % l)


class SessionStoreRedis(SessionStore):
    """ Session storage in Redis

    key-value store. 'session_id': '[atime]:[data]'
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreRedis, self).__init__(storage_url=storage_url)
        try:
            self.engine = StorageEngineRedis(self.storage_url).get_engine()
        except:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)

    def __contains__(self, key):
        return self.engine.exists(key) == 1

    def __getitem__(self, key):
        now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        if self.engine.exists(key) == 1:
            try:
                value = self.engine.get(key)
                atime, data = value.split(':')
                new_value = ':'.join((str(now), data))
                self.engine.set(key, new_value)
                try:
                    self.engine.bgsave()
                except redis.ResponseError:
                    pass
                return self.decode(data)
            except:
                raise KeyError
        else:
            raise KeyError

    def __setitem__(self, key, value):
        now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        pickled = self.encode(value)
        redis_value = ':'.join((str(now), pickled))
        self.engine.set(key, redis_value)
        try:
            self.engine.bgsave()
        except redis.ResponseError:
            pass

    def __delitem__(self, key):
        self.engine.delete(key)
        try:
            self.engine.bgsave()
        except redis.ResponseError:
            pass

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60))
        last_allowed_time = datetime.datetime.utcnow() - timeout
        last_allowed_timestamp = int(time.mktime(last_allowed_time.timetuple()))
        for key in self.engine.keys('*'):
            value = self.engine.get(key)
            #atime = int(value.split(':')[0])
            atime = int(float(value.split(':')[0]))
            if atime < last_allowed_timestamp:
                self.engine.delete(key)


class SessionStoreMongoDB(SessionStore):
    """Session storage in MongoDB
    {'session_id': id, 'atime': time, 'data': data}
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreMongoDB, self).__init__(storage_url=storage_url)
        try:
            store = StorageEngineMongoDB(self.storage_url)
            store.get_engine()
            self.db = store.db
        except:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)

        self.db.whirly_sessions.ensure_index('session_id', unique=True)
        self.collection = self.db.whirly_sessions

    def __contains__(self, key):
        return self.collection.find_one({'session_id': key}) is not None

    def __getitem__(self, key):
        now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        try:
            s = self.collection.find_one({'session_id': key})
            if s:
                data = s['data']
                self.collection.update(
                    {'session_id': key},
                    {'atime': now},
                    upsert=True)
                self.collection.database.connection.end_request()
                return self.decode(data)
            raise KeyError
        except:
            self.collection.database.connection.end_request()
            raise KeyError

    def __setitem__(self, key, value):
        now = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        pickled = self.encode(value)
        self.collection.update(
            {'session_id': key},
            {'session_id': key,
             'atime': now,
             'data': pickled},
             upsert=True)
        self.collection.database.connection.end_request()

    def __delitem__(self, key):
        self.collection.remove({'session_id': key})
        self.collection.database.connection.end_request()

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60))
        last_allowed_time = datetime.datetime.utcnow() - timeout
        last_allowed_timestamp = int(time.mktime(last_allowed_time.timetuple()))
        self.collection.remove({'atime': {'$lte': last_allowed_timestamp}})
        self.collection.database.connection.end_request()


class SessionStoreMemcached(SessionStore):
    """Session storage in memcached
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreMemcached, self).__init__(storage_url=storage_url)
        try:
            self.engine = StorageEngineMemcached(self.storage_url).get_engine()
        except:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)

    def __contains__(self, key):
        return self.engine.get(key) is not None

    def __getitem__(self, key):
        now = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        value = self.engine.get(key)
        if value:
            atime, data = value.split(':', 1)
            decoded_data = self.decode(data)
            lifetime = decoded_data['lifetime'] #XXX right???
            new_value = ':'.join((now, data))
            self.engine.set(key, new_value, time=lifetime)
            return decoded_data
        else:
            raise KeyError

    def __setitem__(self, key, value):
        lifetime = value['lifetime']
        now = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        pickled = self.encode(value)
        mem_value = ':'.join((now, pickled))
        self.engine.set(key, mem_value, time=lifetime)

    def __delitem__(self, key):
        self.engine.delete(key)

    def cleanup(self, timeout):
        pass


class SessionStoreMemcache(SessionStoreMemcached):
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreMemcached, self).__init__(storage_url=storage_url)
        try:
            self.engine = StorageEngineMemcache(self.storage_url).get_engine()
        except:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)


class SessionStoreCookie(SessionStore):
    """Session stored in cookie
    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreCookie, self).__init__(storage_url=storage_url)

    def set_handler(self, handler):
        self.handler = handler
        self.cookie_domain = handler.application.settings.get('cookie_domain')
        self.cookie_path = handler.application.settings.get('cookie_path')

    def __contains__(self, key):
        if self.handler.get_secure_cookie(key):
            return True
        else:
            return False

    def __getitem__(self, key):
        now = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        value = self.handler.get_secure_cookie(key)
        if value:
            atime, data = value.split(':', 1)
            decoded_data = self.decode(data)
            lifetime = decoded_data['lifetime']
            new_value = ':'.join((now, data))
            expires = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=lifetime)
            self.handler.set_secure_cookie(key, new_value, self.cookie_domain,
                expires=expires, path=self.cookie_path)
            return decoded_data
        else:
            raise KeyError

    def __setitem__(self, key, value):
        now = str(time.mktime(datetime.datetime.utcnow().timetuple()))
        lifetime = value['lifetime']
        pickled = self.encode(value)
        mem_value = ':'.join((now, pickled))
        if len(mem_value) > 4064:
            raise SessionStoreError("Cookie value too long to store")
        expires = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=lifetime)
        self.handler.set_secure_cookie(key, mem_value, self.cookie_domain,
            expires=expires, path=self.cookie_path)

    def __delitem__(self, key):
        self.handler.clear_cookie(key)

    def cleanup(self, timeout):
        pass


class SessionStoreDatastore(SessionStore):
    """Session storage in datastore on google appengine

    """
    def __init__(self, storage_url=None, **kw):
        super(SessionStoreDatastore, self).__init__(storage_url=storage_url)
        try:
            self.engine = StorageEngineDatastore(self.storage_url).get_engine()
        except:
            raise SessionStoreError("Could not create connection "
                                      "for: %s " % self.storage_url)

    def __contains__(self, key):
        sessions = self.engine.GqlQuery("SELECT * FROM WhirlySession WHERE session_id = :1", key)
        s = sessions.get()
        if s:
            return True
        else:
            return False

    def __getitem__(self, key):
        now = datetime.datetime.utcnow()
        try:
            q = self.engine.GqlQuery("SELECT * FROM WhirlySession WHERE "
                                     "session_id = :1", key)
            s = q.fetch(limit=1)[0]
            s.atime = now
            self.engine.put(s)
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.utcnow()

        if key in self:
            s = self.engine.GqlQuery("SELECT * from WhirlySession WHERE "
                                     "session_id = :1", key)[0]
            s.atime = now
            s.data = pickled
        else:
            s = WhirlySession(session_id=key)
            s.data = pickled
        self.engine.put(s)

    def __delitem__(self, key):
        q = self.engine.GqlQuery("SELECT * from WhirlySession WHERE "
                                 "session_id = :1", key)
        for s in q:
            s.delete()

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60))
        last_allowed_time = datetime.datetime.utcnow() - timeout
        q = self.engine.GqlQuery("SELECT * FROM WhirlySession WHERE "
                                 "atime < :1", last_allowed_time)
        for s in q:
            s.delete()


storage_cls_map = {
    'cookie': SessionStoreCookie,
    'dir': SessionStoreDirectory,
    'mysql': SessionStoreMySQL,
    #  'postgresql': SessionStorePostgreSQL,
    #  'SQLite': SessionStoreSQLite,
    'redis': SessionStoreRedis,
    'mongodb': SessionStoreMongoDB,
    'memcached': SessionStoreMemcached,
    'datastore': SessionStoreDatastore,
    'gaememcache': SessionStoreMemcache,
    #  sqlalchemy support & various orm support  XXX TODO
}



class SessionStoreDelegateMeta(type):
    def __call__(cls, storage_url='dir://', *args, **kw):
        storage_url = storage_url
        try:
            storage_type = storage_url.split('://')[0].lower()
        except IndexError:
            raise SessionStoreError("Session storage url is invalid. ")
        _log.debug("Session storage backend %s selected" % storage_type)
        _log.debug("Session storage url: %s" % storage_url)

        try:
            return storage_cls_map[storage_type](storage_url, *args, **kw)
        except KeyError:
            return super(SessionStoreMeta, cls).__call__(*args, **kw)


class SessionStoreDelegate(object):
    __metaclass__ = SessionStoreDelegateMeta

    def __init__(self, storage_url=None):
        raise NotImplementedError


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


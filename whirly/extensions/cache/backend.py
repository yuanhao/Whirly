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


import time
import re
import os
import hashlib
import logging

try:
    import cPickle as pickle
except:
    import pickle

from whirly import project
from whirly import utils
from whirly.extensions.storage import StorageEngineError
from whirly.extensions.storage import StorageEngineDelegate



__all__ = ['MemcachedMixIn', 'DirMixIn', 'RedisMixIn',
           'MemcacheMixIn']


class CacheBase(object):
    def __init__(self, timeout=300, **kwargs):
        self.storage_url = project.setting('cache', 'storage_url')
        try:
            self.engine = StorageEngineDelegate(self.storage_url)
        except StorageEngineError:
            raise
        self.timeout = timeout
        self._prepare()

    def __call__(self):
        return self

    def _prepare(self):
        pass


class CacheMixIn:
    def get(self, key, default=None):
        raise NotImplementedError

    def set(self, key, value, timeout=300):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def contains(self, key):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def get_many(self, keys):
        data = {}
        for k in keys:
            value = self.get(k)
            if value:
                d[k] = value
        return data

    def set_many(self, data, timeout=None):
        for k, v in data.items():
            self.set(key, value, timeout)

    def delete_many(self, keys):
        for k in keys:
            self.delete(k)


class Memcached(CacheBase):
    def __call__(self):
        return self.engine


    # def get(self, key, default=None):
        # value = self.engine.get(key)
        # if not value:
            # return default
        # return value

    # def set(self, key, value, timeout=0):
        # if timeout == 0:
            # timeout = self.timeout
        # self.engine.set(key, value, timeout)

    # def delete(self, key):
        # self.engine.delete(key)

    # def contains(self, key):
        # return self.engine.get(key) is not None

    # def clear(self):
        # if session use memcached, will be flushed too XXX
        # self.engine.flush_all()

    # def incr(self, key):
        # self.engine.incr(key)

    # def decr(self, key):
        # self.engine.decr(key)

    # def append(self, key, value):
        # self.engine.append(value)

    # def prepend(self, key, value):
        # self.engine.prepend(value)

    # def set_many(self, data, timeout=0):
        # if timeout == 0:
            # timeout = self.timeout
        # self.engine.set_multi(data, timeout)

    # def delete_many(self, keys):
        # self.engine.delete_multi(keys)


class Memcache(CacheBase):
    def __call__(self):
        return self.engine


class RedisMixIn(CacheBase, CacheMixIn):
    def get(self, key, default=None):
        value = default
        now = time.time()
        data = self.engine.get(key)
        expire_data, value_data = data.split(':', 1)
        expire = pickle.loads(expire_data)
        if expire < now:
            self.delete(key)
        else:
            value = pickle.loads(value_data)
        return value

    def set(self, key, value, timeout=None):
        if not timeout:
            timeout = self.timeout

        self._cleanup()
        now = time.time()
        expire_data = pickle.dumps(now + timeout, pickle.HIGHEST_PROTOCOL)
        value_data = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        self.engine.set(key, ':'.join(expire_data, value_data))

    def delete(self, key):
        self.engine.delete(key)

    def contains(self, key):
        if self.engine.exists(key):
            now = time.time()
            data = self.engine.get(key)
            expire_data = data.split(':', 1)[0]
            expire = pickle.loads(expire_data)
            if expire < now:
                self.delete(key)
                return False
            else:
                return True
        else:
            return False

    def clear(self):
        self.engine.flushdb()

    def _cleanup(self):
        for key in self.engine.keys('*'):
            data = self.engine.get(key)
            expire_data = data.split(':', 1)[0]
            expire = pickle.loads(expire_data)
            now = time.time()
            if expire < now:
                self.engine.delete(key)


class DirMixIn(CacheBase, CacheMixIn):
    def _prepare(self):
        self._prepare_dir()
        self._max_entries = 300

    def _prepare_dir(self):
        url_re = re.compile(r"dir://(.*)")
        match = url_re.match(self.storage_url)
        _path = match.groups()[0]
        if not os.path.exists(_path):
            _path = project.project_directory()
        self.path = os.path.join(_path, 'data')
        self.path = os.path.join(self.path, 'cache')
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        logging.debug('Cache store path: %s' % self.path)

    def _get_path(self, key):
        if os.path.sep in key:
            raise Exception('Bad key %s' % key)
        path = hashlib.md5(key.encode('utf-8')).hexdigest()
        path = os.path.join(path[:2], path[2:4], path[4:])
        return os.path.join(self.path, path)

    def _delete_file(self, path):
        os.remove(path)
        try:
            dirpath = os.path.dirname(path)
            os.rmdir(dirpath)
            os.rmdir(os.path.dirname(dirpath))
        except (IOError, OSError):
            pass

    def get(self, key, default=None):
        filepath = self._get_path(key)
        try:
            f = open(filepath, 'rb')
            expire = pickle.load(f)
            now = time.time()
            if expire < now:
                f.close()
                self._delete_file(filepath)
            else:
                return pickle.load(f)
        except (IOError, OSError, EOFError, pickle.PickleError):
            pass
        return default

    def set(self, key, value, timeout=None):
        if not timeout:
            timeout = self.timeout

        filepath = self._get_path(key)
        dirpath = os.path.dirname(filepath)

        self._cleanup()

        try:
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)
            f = open(filepath, 'wb')
            now = time.time()

            pickle.dump(now + timeout, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)
        except (IOError, OSError):
            pass

    def delete(self, key):
        try:
            self._delete_file(self._get_path(key))
        except (IOError, OSError):
            pass

    def contains(self, key):
        filepath = self._get_path(key)
        try:
            f = open(filepath, 'rb')
            expire = pickle.load(f)
            now = time.time()
            if expire < now:
                f.close()
                self._delete_file(filepath)
                return False
            else:
                return True
        except (IOError, OSError, EOFError, pickle.PickleError):
            return False

    def clear(self):
        try:
            shutil.rmtree(self.path)
        except (IOError, OSError):
            pass

    def _cleanup(self):
        if int(self._num_entries) < self._max_entries:
            return

        try:
            filelist = os.listdir(self.path)
        except (IOError, OSError):
            return

        doomed = [os.path.join(self.path, k) for (i, k) in enumerate(filelist)
                  if i % 3 == 0]
        for topdir in doomed:
            try:
                for root, _, files in os.walk(topdir):
                    for f in files:
                        self._delete_file(os.path.join(root, f))
            except (IOError, OSError):
                pass

    @property
    def _num_entries(self):
        count = 0
        for _, _, files in os.walk(self.path):
            count += len(files)
        return count


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



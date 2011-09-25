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


import os
import time
import logging

from tornado.web import HTTPError

import whirly.web
import whirly.utils

from whirly.extensions.base import Extension
from whirly.extensions.session.store import SessionStoreDelegate


__all__ = ['Session']


class Session(whirly.utils.ThreadedDict):
    def __init__(self, request_handler, **kwargs):
        self.__dict__['_request_handler'] = request_handler
        self.__dict__['_settings'] = self._request_handler.application.settings
        self.__dict__['_last_cleanup_time'] = 0
        self.__dict__['_session_cookie_name'] = self._settings.get(
            'session_cookie_name', 'session_id')
        self.__dict__['_session_storage_url'] = self._settings.get(
            'session_storage_url', 'dir://')
        self.__dict__['_cookie_domain'] = self._settings.get('cookie_domain')
        self.__dict__['_cookie_path'] = self._settings.get('cookie_path', '/')
        self.__dict__['_cookie_expires_days'] = self._settings.get(
            'cookie_expires_days', None)
        self.__dict__['store'] = SessionStoreDelegate(self._session_storage_url)
        if (self._session_storage_url.startswith("cookie")):
            # cookie based session need current handler
            self.store.set_handler(self._request_handler)
        self.session_id = self._request_handler.get_secure_cookie(self._session_cookie_name)
        self.lifetime = self._settings.get('session_lifetime', 7200)
        self._killed = False
        self._cleanup()
        request = self._request_handler.request

        if self.session_id:
            # TODO do we need session id verify here
            logging.debug("Get session id from secure cookie: %s" %
                          self.session_id)
            if  self.session_id not in self.store:
                if self._settings.get('session_ignore_expiry', True):
                    self.session_id = None
                else:
                    logging.debug('User has a id but it is not in store. ')
                    return self.expired()
            else:
                self.update(self.store[self.session_id])
                self._validate_ip(request.remote_ip)
                self._validate_user_agent(request.headers.get('User-Agent'))

        if not self.session_id:
            logging.debug("Session id is invalid or not set, gen a new one")
            self.session_id = self._generate_session_id()

        # always update to the current 
        self.ip = request.remote_ip
        self.user_agent = request.headers.get('User-Agent')
        logging.debug("Session lifetime: %d" % self.lifetime)

    def __repr__(self):
        return '<Session id: %s data: %s>' % (self.session_id, self)

    def __str__(self):
        return self.session_id

    def _cleanup(self):
        """ clean expired sessions
        """
        current_time = time.time()
        lifetime = self.lifetime
        if current_time - self._last_cleanup_time > lifetime:
            self.store.cleanup(lifetime)
            self.__dict__['_last_cleanup_time'] = current_time

    def _generate_session_id(self):
        """Generat a random session id
        """
        while True:
            session_id = os.urandom(32).encode('hex') # 256 bits of entropy
            if session_id not in self.store:
                break
        return session_id

    def _validate_ip(self, remote_ip):
        if self.session_id and self.get('ip') != remote_ip:
            if not self._settings.get('session_ignore_change_ip', True):
                return self.expired()

    def _validate_user_agent(self, user_agent):
        if self.session_id and self.get('user_agent') != user_agent:
            if not self._settings.get('session_ignore_change_useragent', True):
                return self.expired()

    def expired(self):
        """Set current session instance expired
        """
        self._killed = True
        self.save()
        logging.debug("This session is expired")
        raise HTTPError(200, "This session is expired. ")

    def kill(self):
        del self.store[self.session_id]
        self._killed = True
        self.save()

    def save(self):
        if not self.get('_killed'):
            self.store[self.session_id] = dict(self)
            self._request_handler.set_secure_cookie(
                self._session_cookie_name,
                self.session_id,
                domain=self._cookie_domain,
                path=self._cookie_path,
                expires_days=self._cookie_expires_days
            )
        else:
            logging.debug('Clean "session_id" in the cookie of user. ')
            self._request_handler.clear_cookie(self._session_cookie_name)

    def flush(self):
        """Force to delete the current session and make a new one
        """
        self.kill()
        logging.debug("Session data before flush: ")
        logging.debug(self._getd())
        self._getd().clear()
        logging.debug("Session data after flush: ")
        logging.debug(self._getd())

        self._killed = False
        self.session_id = self._generate_session_id()
        self.ip = self._request_handler.request.remote_ip
        self.user_agent = self._request_handler.request.headers.get('User-Agent')
        self.lifetime = self._settings.get('session_lifetime', 7200)
        self.save()


class SessionExtension(Extension):
    def __init__(self):
        # not required, default will be dir storage
        # self.define_required('session_storage_url',
                             # 'Url for session backend storage')
        super(SessionExtension, self).__init__('session')
        # you can append ur transform class here 

    def before(self, handler):
        if not isinstance(handler, whirly.web.StaticFileHandler):
            handler.session = Session(handler)
        return handler


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


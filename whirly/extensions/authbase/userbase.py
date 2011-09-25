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


import random
import hashlib
import logging

from whirly import project


__all__ = ['UserProfile', 'AbstractUserHelper', 'AbstractUser',
           'UserWithStorage', 'AnonymousUser']


SESSION_AUTH_KEY = 'auth_username'
UNUSABLE_PASSWORD = '!'


def get_hexdigest(algorithm, salt, raw_password):
    if algorithm == 'crypt':
        try:
            import crypt
        except ImportError:
            raise ValueError("'Crypt' not supported. ")
        return crypt.crypt(raw_password, salt)
    if algorithm == 'md5':
        return hashlib.md5(salt + raw_password).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(salt + raw_password).hexdigest()
    raise ValueError("Got unknown password algorithm type in password")


def make_random_password(length=10, allowed_chars='abcdefghijklmnopqrstuvwxyz'
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ23456789'):
    return ''.join([choice(allowed_chars) for i in xrange(length)])


def _user_from_twitter(user):
    local_user = {}
    for k, v in user.items():
        if not v or isinstance(v, dict):
            continue
        # if isinstance(v, basestring):
            # local_user[str(k)] = str(v)
        # else:
        local_user[str(k)] = v
    local_user['password'] = UNUSABLE_PASSWORD
    # local_user['full_name'] = str(user['name'])
    local_user['full_name'] = user['name']
    return local_user


def _user_from_google(user):
    # XXX
    raise NotImplementedError
    return user


def _user_from_facebook(user):
    # XXX
    raise NotImplementedError
    return user


def local_user(user_dict, auth_provider):
    local_user_dict = {}
    if auth_provider == 'twitter':
        local_user_dict = _user_from_twitter(user_dict)
    elif auth_provider == 'google':
        local_user_dict = _user_from_google(user_dict)
    elif auth_provider == 'facebook':
        local_user_dict = _user_from_facebook(user_dict)
    else:
        local_user_dict = user_dict
    return local_user_dict


class UserProfileNotAvailable(Exception):
    pass


class UserProfile(object):
    pass


class AbstractUserHelper(object):
    def login(self, user=None):
        """For no storage must overrice and save needed data into session
        """
        if not user:
            return
        self.handler.session[SESSION_AUTH_KEY] = user.username
        self.handler.session.save()

    def logout(self):
        """For no storage must overrice and save needed data into session
        """
        try:
            del self.handler.session[SESSION_AUTH_KEY]
            self.handler.session.save()
        except KeyError:
            pass
        self.handler.user = AnonymousUser()

    def create_user(self, user_dict, auth_provider='local'):
        raise NotImplementedError

    def get_user(self):
        try:
            username = self.handler.session[SESSION_AUTH_KEY]
            user = self.load_user(username)
            if not user:
                user = AnonymousUser()
        except KeyError:
            user = AnonymousUser()
        self.handler.user = user

    def load_user(self, username):
        """Load user data from different storage & create a user object return
        """
        raise NotImplementedError

    def authenticate(username, password):
        """Return user object or None
        """
        raise NotImplementedError


class UserMixIn(object):
    """Create user per create a instance of a user, then save() it
    """
    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def set_unusable_password(self):
        self.password = UNUSABLE_PASSWORD

    def email_user(self, subject, message, from_mail=None):
        raise NotImplementedError

    def __unicode__(self):
        return self.username

    def get_groups(self):
        raise NotImplementedError

    def set_groups(self, value):
        raise NotImplementedError

    groups = property(get_groups, set_groups)

    def get_user_permissions(self):
        raise NotImplementedError

    def set_user_permissions(self, value):
        raise NotImplementedError

    user_permissions = property(get_user_permissions,
                                set_user_permissions)

    def group_permissions(self):
        raise NotImplementedError

    @property
    def permissions(self):
        return set(list(self.user_permissions) + list(self.group_permissions))

    def add_permission(self, permission):
        raise NotImplementedError

    def add_group(self, group):
        raise NotImplementedError

    @property
    def profile(self):
        return None

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    @classmethod
    def exists(cls, username):
        raise NotImplementedError


class AnonymousUser(UserMixIn):
    def __init__(self):
        self.username = ''
        self.is_active = project.setting('auth', 'enable_anonymous_user', True)

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def get_groups(self):
        return set()

    def set_groups(self, value):
        raise NotImplementedError

    groups = property(get_groups, set_groups)

    def get_user_permissions(self):
        return set()

    def set_user_permissions(self, value):
        raise NotImplementedError

    user_permissions = property(get_user_permissions, set_user_permissions)

    @property
    def group_permissions(self):
        return set()

    def add_permission(self, permission):
        raise NotImplementedError

    def add_group(self, group):
        raise NotImplementedError

    def __unicode__(self):
        return 'Anonymous User'

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_anonymous(self):
        return True

    def is_authenticated(self):
        return False


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



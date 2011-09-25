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


import logging
import sys
import re
import datetime
import random
import hashlib

from pymongo import GEO2D
from pymongo.objectid import ObjectId
from mongokit import Connection, Document

from whirly import project
from whirly.extensions.base import Extension
from whirly.extensions.authbase.userbase import SESSION_AUTH_KEY
from whirly.extensions.authbase.userbase import AbstractUserHelper
from whirly.extensions.authbase.userbase import local_user, get_hexdigest
from whirly.extensions.authbase.permissionbase import AbstractPermissionHelper
from whirly.extensions.authbase.groupbase import AbstractGroupHelper

conn = Connection()
_db_url = project.setting('database', 'database_url')
_auth_db = re.match('mongodb://([\S|\.]+?)?(?::(\d+))?/(\S+)', _db_url).group(3)
zidb = conn[_auth_db]
user_collection = zidb['whirly_auth_user']
group_collection = zidb['whirly_auth_group']
permission_collection = zidb['whirly_auth_permission']


__all__ = ['User', 'Group', 'Permission', 'Auth']


class Permission(Document):
    structure = {
        'name': unicode,
        'description': unicode,
    }
    required_fields = ['name']
    atomic_save = True
    use_dot_notation=True


class Group(Document):
    structure = {
        'name': unicode,
        'description': unicode,
        'is_active': bool,
        'permissions': [unicode],
    }
    required_fields = ['name']
    default_values = { 'is_active': True }
    atomic_save = True
    use_dot_notation=True

    def add_permission(self, permission):
        self['permissions'].append(permission['name'])
        self.save()


class User(Document):
    structure = {
        'username': unicode,
        'created': datetime.datetime,
        'password': unicode,
        'verified': bool,
        'email': unicode,
        'is_staff': bool,
        'is_active': bool,
        'is_superuser': bool,
        'permissions': [unicode],
        'groups': [Group],
        'profile': dict,
        'loc': list,
        'followers': [ObjectId],
    }
    required_fields = ['username']
    default_values = {
        'created': datetime.datetime.utcnow,
        'is_staff': False,
        'is_active': True,
        'is_superuser': False,
        'verified': False,
    }
    gridfs = {
        'files':['original_avatar', 'normal_avatar',
                 'medium_avatar', 'mini_avatar']
    }
    use_autorefs = True
    atomic_save = True
    use_dot_notation=True
    indexes = [
        {
            'fields': ['username'],
            'unique': True,
        },
        {
            'fields': ['followers'],
            'unique': False,
        },
    ]

    def add_permission(self, permission):
        self['permissions'].append(permission['name'])
        self.save()

    def add_group(self, group):
        self['groups'].append(group)
        self.save()

    @property
    def group_permissions(self):
        if not hasattr(self, '_group_permissions'):
            self._group_permissions = set()
            for group in self['groups']:
                for perm in group['permissions']:
                    self._group_permissions.add(perm)
        return self._group_permissions

    @classmethod
    def exists(cls, username):
        return user_collection.find_one({'username': username })

    def set_password(self, raw_password):
        algo = project.setting('auth', 'password_algorithm_type', 'sha1')
        salt = get_hexdigest(algo, str(random.random()), str(random.random()))[:5]
        hsh = get_hexdigest(algo, salt, raw_password)
        self['password'] = u'%s$%s$%s' % (algo, salt, hsh)

    def check_password(self, raw_password):
        algo, salt, hsh = self['password'].split('$')
        return hsh == get_hexdigest(algo, salt, raw_password)

    def set_unusable_password(self):
        self['password'] = UNUSABLE_PASSWORD
        self.save()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def followers_count(self):
        return len(self.followers)

    def following_count(self):
        return user_collection.find({'followers': self._id}).count()

    @property
    def following(self):
        return user_collection.User.find({'followers': self._id})

    @property
    def follower_list(self):
        return user_collection.User.find({'_id': {'$in': self.followers }})


class UserHelper(AbstractUserHelper):
    def load_user(self, username):
        return user_collection.User.find_one({ 'username': username })

    def create_user(self, *args, **kwargs):
        raise NotImplementedError

    def update_user(self, *args, **kwargs):
        raise NotImplementedError


class PermissionHelper(AbstractPermissionHelper):
    def create_permission(self, *args, **kwargs):
        raise NotImplementedError


class GroupHelper(AbstractGroupHelper):
    def create_group(self, *args, **kwargs):
        raise NotImplementedError


class AuthHelper(UserHelper, PermissionHelper, GroupHelper):
    def __init__(self, handler):
        self.handler = handler


class Auth(Extension):
    def __init__(self):
        if not project.setting('extensions', 'whirly.extensions.session'):
            raise Exception("Auth Extension need session support. ")
        super(Auth, self).__init__('auth')

    def before(self, handler):
        handler.auth = AuthHelper(handler)
        handler.auth.get_user()
        return handler


user_collection.create_index([("loc", GEO2D)])
conn.register([User, Permission, Group])


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



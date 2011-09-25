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
import  sys

try:
    import cPickle as pickle
except:
    import pickle

from google.appengine.ext import db

from whirly import project
from whirly.extensions.base import Extension
from whirly.extensions.authbase.userbase import SESSION_AUTH_KEY
from whirly.extensions.authbase.userbase import AbstractUserHelper
from whirly.extensions.authbase.userbase import UserProfile
from whirly.extensions.authbase.userbase import UserProfileNotAvailable
from whirly.extensions.authbase.userbase import local_user, get_hexdigest
from whirly.extensions.authbase.permissionbase import AbstractPermissionHelper
from whirly.extensions.authbase.groupbase import AbstractGroupHelper


__all__ = ['User', 'Group', 'Permission', 'DatastoreAuth']

class PickleProperty(db.BlobProperty):
    def get_value_for_datastore(self, model_instance):
        value = super(PickleProperty, self).get_value_for_datastore(model_instance)
        return pickle.dumps(value)

    def make_value_from_datastore(self, value):
        value = super(PickleProperty, self).make_value_from_datastore(value)
        return pickle.loads(value)

    def validate(self, value):
        try:
            pickle.dumps(value)
        except pickle.PicklingError:
            raise
        return value


class Permission(db.Model):
    name = db.StringProperty(required=True, indexed=True) #unique
    description = db.StringProperty()
    users = db.ListProperty(db.Key)
    groups = db.ListProperty(db.Key)

    def save(self):
        self.put()

    def __unicode__(self):
        return self.name


class UserProfileDatastore(UserProfile):
    @classmethod
    def get_by_key_name(cls, key_name):
        raise UserProfileNotAvailable("Not implemented for datastore")


class User(db.Model):
    username = db.StringProperty(required=True, indexed=True) #unique
    password = db.StringProperty()
    email = db.EmailProperty(indexed=True)
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    full_name = db.StringProperty()
    is_staff = db.BooleanProperty(default=False, indexed=True)
    is_active = db.BooleanProperty(default=True)
    is_superuser = db.BooleanProperty(default=False, indexed=True)
    auth_data = PickleProperty()
    groups = db.ListProperty(db.Key)

    def save(self):
        self.put()

    @property
    def permissions(self):
        return PermissionModel.gql("WHERE users = :1", self.key())

    def add_group(self, group):
        if group not in self.groups:
            self.groups.append(group)

    def add_permission(self, permission):
        if self not in permission.users:
            permission.users.append(self)
            permission.put()

    @property
    def group_permissions(self):
        if not hasattr(self, '_group_permissions'):
            self._group_permissions = set()
            for group in self.groups:
                for permission in group.permissions:
                    self._group_permissions.add(permission)
        return self._group_permissions

    def __unicode__(self):
        return self.username

    @classmethod
    def exists(cls, username):
        u = User.gql("username = :1", username).get()
        if u:
            return True
        else:
            return False

    def set_password(self, raw_password):
        algo = project.setting('auth', 'password_algorithm_type', 'sha1')
        salt = get_hexdigest(algo, str(random.random()), str(random.random()))[:5]
        hsh = get_hexdigest(algo, salt, raw_password)
        self.password = '%s$%s$%s' % (algo, salt, hsh)

    def check_password(self, raw_password):
        algo, salt, hsh = self.password.split('$')
        return hsh == get_hexdigest(algo, salt, raw_password)

    def set_unusable_password(self):
        self.password = UNUSABLE_PASSWORD

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    @property
    def profile(self):
        if not hasattr(self, '_profile_cache'):
            profile_module_string = project.setting('auth', 'profile_class', None)
            if profile_module_string:
                try:
                    module_name, sep, class_name = profile_module_string.rpartition('.')
                except ValueError:
                    raise UserProfileNotAvailable("'%s' seems not valid."
                          " " % profile_module_string)

                try:
                    __import__(module_name)
                    module = sys.modules[module_name]
                    cls = module.__dict__[class_name]
                except ImportError, KeyError:
                    raise UserProfileNotAvailable("Cannot import %s. "
                          " " % profile_module_string)
            else:
                cls = UserProfileDatastore
            self._profile_cache = cls.get_by_key_name("profileof%s" % self.username)
        return self._profile_cache


class Group(db.Model):
    name = db.StringProperty(required=True, indexed=True) #unique
    description = db.StringProperty()
    is_active = db.BooleanProperty(default=True)

    @property
    def permissions(self):
        return PermissionModel.gql("WHERE groups = :1", self.key())

    @property
    def users(self):
        return User.gql("WHERE groups = :1", self.key())

    def save(self):
        self.put()

    def add_permission(self, permission):
        if self not in permission.groups:
            permission.groups.append(self)
            permission.put()

    def add_user(self, user):
        if self not in user.groups:
            user.groups.append(self)
            user.put()


class UserHelper(AbstractUserHelper):
    def load_user(self, username):
        return User.gql("WHERE username = :1", username).get()

    def create_user(self, user_dict, auth_provider='local'):
        local_user_dict = local_user(user_dict, auth_provider)
        logging.debug('CREATE NEW USER')
        user = User(**local_user_dict)
        if auth_provider != 'local':
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
        user.put()

    def update_user(self, user, user_dict, auth_provider='local'):
        local_user_dict = local_user(user_dict, auth_provider)
        for k, v in local_user_dict.items():
            if k in user.properties().keys():
                setattr(user, k, v)
        user.save()


class PermissionHelper(AbstractPermissionHelper):
    def create_permission(self, name, description=None):
        perm = Permission(name=name, description=description)
        perm.put()


class GroupHelper(AbstractGroupHelper):
    def create_group(self, name, description=None, is_active=True):
        group = Group(name=name, description=description, is_active=is_active)
        group.put()


class AuthHelper(UserHelper, PermissionHelper, GroupHelper):
    def __init__(self, handler):
        self.handler = handler


class DatastoreAuth(Extension):
    def __init__(self):
        if not project.setting('extensions', 'whirly.extensions.session'):
            raise Exception("Auth extension need session support. ")
        super(DatastoreAuth, self).__init__('auth')

    def before(self, handler):
        handler.auth = AuthHelper(handler)
        handler.auth.get_user()
        return handler


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



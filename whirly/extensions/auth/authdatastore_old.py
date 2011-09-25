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

try:
    import cPickle as pickle
except:
    import pickle

from google.appengine.ext import db

from whirly import project
from whirly.extensions.base import Extension
from whirly.extensions.authbase.userbase import SESSION_AUTH_KEY
from whirly.extensions.authbase.userbase import AbstractUser
from whirly.extensions.authbase.userbase import AbstractUserHelper
from whirly.extensions.authbase.userbase import local_user
from whirly.extensions.authbase.permissionbase import AbstractPermission
from whirly.extensions.authbase.permissionbase import AbstractPermissionHelper
from whirly.extensions.authbase.groupbase import AbstractGroup
from whirly.extensions.authbase.groupbase import AbstractGroupHelper


__all__ = ['User', 'Group', 'Permission','AuthHelper', 'DatastoreAuth',
           'UserModel', 'PermissionModel', 'GroupModel']


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


class PermissionModel(db.Model):
    name = db.StringProperty(required=True, indexed=True) #unique
    description = db.StringProperty()
    users = db.ListProperty(db.Key)
    groups = db.ListProperty(db.Key)


class UserModel(db.Model):
    username = db.StringProperty(required=True, indexed=True) #unique
    password = db.StringProperty()
    email = db.EmailProperty(indexed=True)
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    full_name = db.StringProperty()
    profile_image_url = db.StringProperty()
    url = db.LinkProperty()
    lang = db.StringProperty()
    time_zone = db.StringProperty()
    utc_offset = db.IntegerProperty()
    location = db.StringProperty()
    description = db.TextProperty()
    is_staff = db.BooleanProperty(default=False, indexed=True)
    is_active = db.BooleanProperty(default=True)
    is_superuser = db.BooleanProperty(default=False, indexed=True)
    # auth_data = db.BlobProperty()
    auth_data = PickleProperty()

    groups = db.ListProperty(db.Key)

    @property
    def permissions(self):
        return PermissionModel.gql("WHERE users = :1", self.key())


class GroupModel(db.Model):
    name = db.StringProperty(required=True, indexed=True) #unique
    description = db.StringProperty()
    is_active = db.BooleanProperty(default=True)

    @property
    def permissions(self):
        return PermissionModel.gql("WHERE groups = :1", self.key())

    @property
    def users(self):
        return UserModel.gql("WHERE groups = :1", self.key())


class Permission(AbstractPermission):
    def __init__(self, name):
        super(Permission, AbstractPermission).__init__(name)
        q = PermissionModel.gql("WHERE name = :1", name)
        self._instance = q.fetch(1)
        self.description = self._permission_instance.description

    def save(self):
        self._instance.name = self.name
        self._instance.description = self.description
        self._instance.put()

    def delete(self):
        self._instance.delete()


class User(AbstractUser):
    def __init__(self, username):
        super(User, self).__init__(username)
        q = UserModel.gql("WHERE username = :1", self.username)
        self._instance = q.get()
        self._load_data_from_datastore()

        for g in self._instance.groups:
            self._groups.add(Group(g.name))
            for p in g.permissions:
                self._group_permissions.add(Permission(p.name))
        for p in self._instance.permissions:
            self._user_permissions.add(Permission(p.name))

    def save(self):
        for k, v in self._user_dict.items():
            if k in self._instance.properties().keys() and k != 'auth_data':
                setattr(self._instance, k, v)
        self._instance.put()

    def _load_data_from_datastore(self):
        for k in self._instance.properties().keys():
            if k not in ['auth_data', 'groups']:
                setattr(self, k, getattr(self._instance, k, None))
        # pickle_auth_data = self._instance.auth_data
        # self.auth_data = pickle.loads(pickle_auth_data)
        self.auth_data = self._instance.auth_data
        logging.debug(self.auth_data)

    def delete(self):
        self._instance.delete()

    def get_groups(self):
        return self._groups

    def set_groups(self, value):
        if not isinstance(value, set):
            value = set(value)
        self._groups = value
        self._instance.groups = []
        for g in value:
            if g._instance not in self._instance.groups:
                self._instance.groups.append(g._instance)
        self.save()

    def get_user_permissions(self):
        return self._user_permissions

    def set_user_permissions(self, value):
        if not isinstance(value, set):
            value = set(value)
        self._user_permissions = value
        for p in value:
            if self._instance not in p._instance.users:
                p._instance.users.append(self._instance)
                p._instance.put()

    def group_permissions(self):
        return self._group_permissions

    def add_permission(self, permission):
        if not isinstance(permission, Permission):
            raise TypeError
        self._user_permissions.add(permission)
        if self._instance not in permission._instance.users:
            permission._instance.users.append(self._instance)
            permission._instance.put()

    def add_group(self, group):
        if not isinstance(permission, Group):
            raise TypeError
        self._groups.add(group)
        if group._instance not in self._instance.groups:
            self._instance.groups.append(group._instance)
            self.save()

    @classmethod
    def exists(cls, username):
        q = UserModel.gql("WHERE username = :1", username)
        if q.count() == 0:
            return False
        else:
            return True


# class Group(AbstractGroup):
    # def __init__(self, name):
        # super(Group, self).__init__(name)
        # q = GroupModel.gql("WHERE name = :1", name)
        # self._instance = q.fetch(1)
        # self.description = self._instance.description
        # self.is_active = self._instance.is_active

        # for p in self._instance.permissions:
            # self._permissions.add(Permission(p.name))
        # for u in self._instance.users:
            # self._users.add(User(u.username))

    # def save(self):
        # self._instance.name = self.name
        # self._instance.description = self.description
        # self._instance.is_active = self.is_active
        # self._instance.put()

    # def delete(self):
        # self._instance.delete()

    # def get_permissions(self):
        # return self._permissions

    # def set_permissions(self, value):
        # if not isinstance(value, set):
            # value = set(value)
        # self._permissions = value
        # for p in value:
            # if self.instance not in p._instance.groups:
                # p._instance.groups.append(self._instance)
            # p.save()

    # def add_permission(self, permission):
        # self._permissions.add(permission)
        # if self.instance not in permission._instance.groups:
            # permission._instance.groups.append(self._instance)
            # permission.save()


class UserHelper(AbstractUserHelper):
    def login(self, user=None):
        self.handler.session[SESSION_AUTH_KEY] = user.username
        self.handler.session.save()

    def logout(self):
        """Normally you dont need to override this if you use db backend
        """
        try:
            del self.handler.session[SESSION_AUTH_KEY]
            self.handler.session.save()
        except KeyError:
            pass
        self.handler.user = AnonymousUser()

    def load_user(self, username):
        return User(username)

    def create_user(self, user_dict, auth_provider='local'):
        local_user_dict = local_user(user_dict, auth_provider)
        logging.debug('CREATE NEW USER')
        user = UserModel(**local_user_dict)
        if auth_provider != 'local':
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
        user.put()

    def update_user(self, userobj, user_dict, auth_provider='local'):
        local_user_dict = local_user(user_dict, auth_provider)
        userobj._user_dict.update(local_user_dict)
        userobj.save()


class PermissionHelper(AbstractPermissionHelper):
    def create_permission(self, name, description=None):
        p = PermissionModel(name=name, description=description)
        p.put()


class GroupHelper(AbstractGroupHelper):
    def create_group(self, name, description=None, is_active=True):
        g = GroupModel(name=name, description=description, is_active=is_active)
        g.put()


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



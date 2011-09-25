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


from whirly import project
from whirly.extensions.base import Extension
from whirly.extensions.authbase.userbase import AbstractUser
from whirly.extensions.authbase.userbase import AbstractUserHelper
from whirly.extensions.authbase.userbase import local_user
from whirly.extensions.authbase.permissionbase \
     import AbstractPermission, AbstractPermissionHelper
from whirly.extensions.authbase.groupbase import AbstractGroup
from whirly.extensions.authbase.groupbase import AbstractGroupHelper


__all__ = ['User', 'Group', 'Permission','AuthHelper', 'NoDB']


class User(AbstractUser):
    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def set_password(self, raw_password):
        raise NotImplementedError

    def check_password(self, raw_password):
        raise NotImplementedError

    def get_groups(self):
        return self._groups

    def set_groups(self, value):
        if not isinstance(value, set):
            value = set(value)
        self._groups = value

    groups = property(get_groups, set_groups)

    def get_user_permissions(self):
        return self._user_permissions

    def set_user_permissions(self, value):
        if not isinstance(value, set):
            value = set(value)
        self._user_permissions = value

    user_permissions = property(get_user_permissions, set_user_permissions)

    @property
    def group_permissions(self):
        return self._group_permissions

    def add_permission(self, permission):
        raise NotImplementedError

    def add_group(self, group):
        raise NotImplementedError


class Permission(AbstractPermission):
    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError


class Group(AbstractGroup):
    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def get_permissions(self):
        return self._permissions

    def set_permissions(self, permissions):
        if not isinstance(permissions, set):
            permissions = set(permissions)
        self._permissions = permissions

    permissions = property(get_permissions, set_permissions)

    # def get_users(self):
        # return self._users

    # def set_users(self, users):
        # if not isinstance(users, set):
            # users = set(users)
        # self._users = users

    # users = property(get_users, set_users)


class UserHelper(AbstractUserHelper):
    def login(self, user=None):
        """Normally you dont need to override this if you use db backend
        """
        self.handler.session[SESSION_AUTH_KEY] = user.username
        # save somethings useful in session for the use of webapp
        # self.handler.session['user_firstname'] = user.first_name
        # self.handler.session['user_lastname'] = user.last_name
        self.handler.session.save()

    def logout(self):
        """Normally you dont need to override this if you use db backend
        """
        try:
            del self.handler.session[SESSION_AUTH_KEY]
            # del self.handler.session['user_firstname']
            # del self.handler.session['user_lastname']
            self.handler.session.save()
        except KeyError:
            pass
        self.handler.user = AnonymousUser()

    def load_user(self, username):
        # fill user
        return User(username) # with different storage type overrice this method

    def authenticate(username, password):
        raise NotImplementedError


class AuthHelper(UserHelper, AbstractPermissionHelper):
    def __init__(self, handler):
        self.handler = handler


class NoDB(Extension):
    def __init__(self):
        if not project.setting('extensions', 'whirly.extensions.session'):
            raise Exception("Auth extension need session support. ")
        super(NoDB, self).__init__('auth')

    def before(self, handler):
        handler.auth = AuthHelper(handler)
        handler.auth.get_user()
        return handler


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



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


__all__ = ['AbstractGroup', 'AbstractGroupHelper']


class AbstractGroupHelper(object):
    def create_group(self, name, description=None, is_active=True):
        raise NotImplementedError


class GroupMixIn:
    # self.name = name
    # self.description = None
    # self.is_active = True
    # self._permissions = set()
    # self._users = set()
    def __unicode__(self):
        return self.name

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def get_permissions(self):
        raise NotImplementedError

    def set_permissions(self):
        raise NotImplementedError

    permissions = property(get_permissions, set_permissions)

    # def get_users(self):
        # raise NotImplementedError

    # def set_users(self):
        # raise NotImplementedError

    # users = property(get_users, set_users)

    def add_permission(self, permission):
        self._permissions.add(permission)

    # def add_user(self, user):
        # self._users.add(user)



### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



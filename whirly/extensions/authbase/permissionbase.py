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

from tornado.web import HTTPError

from whirly import project


__all__ = ['AbstractPermissionHelper', 'InUsers', 'IsSuperUser', 'IsStaff',
           'Authenticated', 'InGroup', 'FromIP', 'BetweenTimes',
           'HasPermission', 'All', 'Any', 'PermissionChecker']


class PermissionSetupError(Exception):
    pass


class AbstractPermissionHelper(object):
    def has_permission(self, permission):
        try:
            permission.check(self.handler)
            return True
        except:
            return False

    def check_permission(self, permission):
        permission.check(self.handler)

    def create_permission(self, name, description=None):
        raise NotImplementedError

class PermissionChecker(object):
    def __init__(self, *args, **kwargs):
        self.message = kwargs.get('message', '')

    def check(self, handler):
        raise NotImplementedError


class InUsers(PermissionChecker):
    def __init__(self, users, *args, **kwargs):
        super(InUsers, self).__init__(*args, **kwargs)

        if isinstance(users, list) or isinstance(users, tuple):
            users_ = []
            for user in users:
                users_.append(user.lower())
            self.allowed_users = users_
        elif isinstance(users, basestring):
            self.allowed_users= [users]
        else:
            raise PermissionSetupError("Expected users to be a list or a "
                                       "string, not a %s" % users)

    def check(self, handler):
        if handler.user.is_authenticated():
            if handler.user.username not in self.allowed_users:
                raise HTTPError(403, self.message)
        else:
            raise HTTPError(401, self.message)


class IsStaff(PermissionChecker):
    def check(self, handler):
        if handler.user.is_authenticated():
            if not handler.user.is_staff:
                raise HTTPError(403, self.message)
        else:
            raise HTTPError(401, self.message)


class IsSuperUser(PermissionChecker):
    def check(self, handler):
        if handler.user.is_authenticated():
            if not handler.user.is_superuser:
                raise HTTPError(403, self.message)
        else:
            raise HTTPError(401, self.message)


class Authenticated(PermissionChecker):
    def check(self, handler):
        if not handler.user.is_authenticated() or not handler.user.is_active:
            raise HTTPError(401, self.message)


class InGroup(PermissionChecker):
    def __init__(self, groups, *args, **kwargs):
        super(InGroup, self).__init__(*args, **kwargs)

        if isinstance(groups, list) or isinstance(groups, tuple):
            groups_ = []
            for group in groups:
                if isinstance(group, basestring):
                    groups_.append(group.lower())
                else:
                    groups_.append(group.name.lower())
            self.allowed_groups = groups_
        elif isinstance(groups, basestring):
            self.allowed_groups = [groups]
        else:
            raise PermissionSetupError("Expected users to be a list or a "
                                       "string, not a %s" % users)

    def check(self, handler):
        if handler.user.is_authenticated():
            user_groups = [g.name.lower() for g in handler.user.groups if g.is_active]
            not_in_group = True
            for user_group in user_groups:
                if user_group in self.allowed_groups:
                    not_in_group = False
            if not_in_group:
                raise HTTPError(403, self.message)
        else:
            raise HTTPError(401, self.message)


class FromIP(PermissionChecker):
    def __init__(self, hosts, key='remote_ip', *args, **kwargs):
        super(FromIP, self).__init__(*args, **kwargs)
        if not isinstance(self.hosts, (list, tuple)):
            hosts = [hosts]
        self.hosts = hosts
        self.key = key

    def check(self, handler):
        user_ip = getattr(handler.request, self.key)
        if not user_ip in self.hosts:
            raise HTTPError(403, self.message)


class BetweenTimes(PermissionChecker):
    """`start` und `end` are datetime.time objects
    """
    def __init__(self, start, end, *args, **kwargs):
        super(BetweenTimes, self).__init__(*args, **kwargs)
        self.start_time = start
        self.end_time = end

    def check(self, handler):
        utcnow = datetime.datetime.utcnow()
        now = datetime.time(
            utcnow.hour,
            utcnow.minute,
            utcnow.second,
            utcnow.microsecond)
        if self.end_time > self.start_time:
            if now < self.start or now >= self.end:
                raise HTTPError(403, self.message)
        else:
            if now < datetime.time(23, 59, 59, 999999) and now >= self.start_time:
                pass
            elif now >= datetime.time(0) and now < self.end_time:
                pass
            else:
                raise HTTPError(403, self.message)


class HasPermission(PermissionChecker):
    def __init__(self, permissions, *args, **kwargs):
        super(HasPermission, self).__init__(*args, **kwargs)
        if isinstance(permissions, list) or isinstance(permissions, tuple):
            permissions_ = []
            for p in permissions:
                if isinstance(p, basestring):
                    permissions_.append(p.lower())
                else:
                    permissions_.append(p.name.lower())
            self.permissions = permissions_
        elif isinstance(permissions, basestring):
            self.permissions = [permissions]
        else:
            raise PermissionSetupError("Expected permissions to be a list or "
                                       "a string.")

    def check(self, handler):
        if handler.user.is_authenticated():
            user_permissions = [p.name for p in handler.user.permissions]
            haved = [p for p in self.permissions if p in user_permissions]
            if len(haved) != len(self.permissions):
                raise HTTPError(403, self.message)
        else:
            raise HTTPError(401, self.message)


class All(PermissionChecker):
    def __init__(self, *permissions):
        if len(permissions) < 2:
            raise PermissionSetupError("Expected at least 2 permission objects")
        permissions = list(permissions)
        permissions.reverse()
        self.permissions = permissions

    def check(self, handler):
        for permission in self.permissions:
            permission.check(handler)


class Any(PermissionChecker):
    def __init__(self, *permissions):
        if len(permissions) < 2:
            raise PermissionSetupError("Expected at least 2 permission objects")
        permissions = list(permissions)
        permissions.reverse()
        self.permissions = permissions

    def check(self, handler):
        error_message = ''
        for permission in self.permissions:
            try:
                permission.check(handler)
                return
            except HTTPError, e:
                error_message += e.message
            except:
                pass
        raise HTTPError(403, message)


class PermissionMixIn:
    # self.name = name
    # self.description = None
    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def __unicode__(self):
        return self.name


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



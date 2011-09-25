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


import sys

from whirly.extensions.authbase.userbase import UserProfile, AnonymousUser
from whirly.extensions.authbase.decorators import with_permission
from whirly.extensions.authbase.permissionbase import InUsers, IsSuperUser
from whirly.extensions.authbase.permissionbase import IsStaff, Authenticated
from whirly.extensions.authbase.permissionbase import InGroup, FromIP
from whirly.extensions.authbase.permissionbase import BetweenTimes, HasPermission
from whirly.extensions.authbase.permissionbase import All, Any
from whirly.extensions.authbase.permissionbase import PermissionChecker
from whirly import project


serve_type = project.setting('application', 'serve_type', 'tornado')
if serve_type == 'wsgi':
    from gaema.auth import OpenIdMixin
    from gaema.auth import OAuthMixin
    from gaema.auth import TwitterMixin
    from gaema.auth import FriendFeedMixin
    from gaema.auth import GoogleMixin
    from gaema.auth import FacebookMixin
    from gaema.webapp_auth import WebappAuth, RequestRedirect, HttpException
else:
    from tornado.auth import OpenIdMixin
    from tornado.auth import OAuthMixin
    from tornado.auth import TwitterMixin
    from tornado.auth import FriendFeedMixin
    from tornado.auth import GoogleMixin
    from tornado.auth import FacebookMixin


def _get_auth_module():
    _extension_settings = project.extension_settings('extensions')
    _auth_module_string  = None
    for key in _extension_settings.keys():
        key_list = key.split('.')
        if 'auth' in key_list:
            _auth_module_string = key
            break

    __import__(_auth_module_string)
    auth_module = sys.modules[_auth_module_string]
    return auth_module


def _get_classes():
    auth_module = _get_auth_module()
    User = auth_module.__dict__['User']
    Group = auth_module.__dict__['Group']
    Permission = auth_module.__dict__['Permission']
    return User, Group, Permission


User, Group, Permission = _get_classes()


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



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


from tornado.web import HTTPError


__all__ = ['with_permission']


class with_permission(object):
    def __init__(self, permission):
        self.permission = permission

    def __call__(self, func):
        def _check(handler, *args, **kwargs):
            login_url = handler.application.settings.get('login_url')
            try:
                self.permission.check(handler)
            except HTTPError, e:
                if e.status_code == 401:
                    if login_url:
                        handler.set_cookie("login_redirect", handler.request.path)
                        return handler.redirect(login_url)
                    else:
                        raise
                elif e.status_code == 403:
                    # display error page or something else
                    raise
                else:
                    # display error page
                    raise
            else:
                return func(handler, *args, **kwargs)
        return _check


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:




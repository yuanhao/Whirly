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


import httplib
import logging

from tornado.wsgi import HTTPRequest, WSGIContainer

from whirly.web import Application


class WSGIApplication(Application):
    def __init__(self, handlers=None, default_host="", extensions=None,
                 **settings):
        super(WSGIApplication, self).__init__(handlers, default_host,
            [], extensions, wsgi=True, **settings)

    def __call__(self, environ, start_response):
        handler = Application.__call__(self, HTTPRequest(environ))
        status = "%s %s" % (str(handler._status_code),
                            httplib.responses[handler._status_code])
        headers = handler._headers.items()
        for cookie_dict in getattr(handler, "_new_cookies", []):
            for cookie in cookie_dict.values():
                headers.append(("Set-Cookie", cookie.OutputString(None)))
        start_response(status, headers)
        return handler._write_buffer


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


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



import os
import logging
import httplib
import traceback

import tornado.template
import tornado.web

from whirly import project
from whirly import helpers
from whirly import utils


class HTTPErrorWrapper(Exception):
    def __init__(self, status_code, format_exc, log_message="", response=None):
        self.status_code = status_code
        self.format_exc = format_exc
        self.log_message = log_message
        self.response = response


class BaseHandler(tornado.web.RequestHandler):
    """ Base request handler of whirly framework.
    """
    def render_string(self, template_name, **kwargs):
        return self.application.template_engine.render_string(template_name,
            self, **kwargs)

    def send_error(self, status_code=500, **kwargs):
        e = kwargs.get('exception', Exception())
        format_exc = traceback.format_exc().splitlines()
        response = None
        if isinstance(e, tornado.web.HTTPError):
            response = e.response
        raise HTTPErrorWrapper(status_code, format_exc, e.message, response)

    @property
    def arguments(self):
        d = dict((k, map(lambda x: x.decode('utf8'), v))
                 for k, v in self.request.arguments.items())
        if not hasattr(self, '_arguments_multidict'):
            self._arguments_multidict = utils.MultiDict(d)
        return self._arguments_multidict


class ErrorPage(BaseHandler):
    def __init__(self, application, request, status_code, message=None,
                 format_exc=[]):
        super(ErrorPage, self).__init__(application, request)
        self.set_status(status_code)
        self.status_message = message
        self.format_exc = format_exc
        self.is_debug = project.setting('application', 'debug', True)
        self._headers.update(utils.no_cache_headers())

    def get(self):
        title = httplib.responses[self._status_code]
        title = "%d %s" % (self._status_code, title)
        if self.status_message:
            title = "%s: %s" % (title, self.status_message)
        traceback_info  = "<br />".join(self.format_exc)

        # is there has some way to custom template load path
        # write more method in handler XXX
        tmpl_path = os.path.join(os.path.dirname(__file__), 'templates')
        tmpl  = tornado.template.Loader(tmpl_path).load("error.html")
        args = dict(
            handler=self,
            request=self.request,
            title=title,
            traceback_info=traceback_info,
            is_debug=self.is_debug,
        )
        self.finish(tmpl.generate(**args))


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



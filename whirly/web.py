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
import sys
import logging
import traceback
import urllib

from tornado.web import RequestHandler, ErrorHandler
from tornado.web import RedirectHandler, StaticFileHandler
from tornado.web import FallbackHandler
from tornado.web import HTTPError, OutputTransform
from tornado.web import UIModule, URLSpec
from tornado.web import Application as TornadoApplication
from tornado.web import asynchronous
from tornado.web import url

import whirly.project
from whirly import helpers as h
from whirly.options import define, options
from whirly.utils import ThreadedDict
from whirly.template import TemplateEngineDelegate
from whirly.handlers import BaseHandler, ErrorPage, HTTPErrorWrapper


class Application(TornadoApplication):
    def __init__(self, handlers=None, default_host="", transforms=None,
                 extensions=None, wsgi=False, **settings):
        if not handlers:
            logging.error("Routes for your project is not configured.")
            sys.exit(1)

        settings = self._adjust_settings(settings)
        default_host = settings.pop('default_host')
        super(Application, self).__init__(handlers, default_host, transforms,
                                          wsgi, **settings)
        self._load_extensions(extensions)

        if not settings.get('test'):
            self._load_template_engine()
        else:
            logging.info("Application running for test")

    def __call__(self, request):
        """Called by HTTPServer to execute the request."""
        logging.debug("\n\nAPPLICAION\n\n")
        logging.debug(h.escape.url_unescape(request.path))
        # maybe bug 
        request.path = h.escape.url_unescape(request.path)

        transforms = [t(request) for t in self.transforms]
        handler = None
        args = []
        kwargs = {}
        handlers = self._get_host_handlers(request)
        if not handlers:
            handler = RedirectHandler(request, "http://%s/" % self.default_host)
        else:
            for spec in handlers:
                match = spec.regex.match(request.path)
                if match:
                    def unquote(s):
                        if s is None: return s
                        return urllib.unquote(s)
                    handler = spec.handler_class(self, request, **spec.kwargs)

                    kwargs = dict((k, unquote(v))
                                  for (k, v) in match.groupdict().iteritems())
                    if kwargs:
                        args = []
                    else:
                        args = [unquote(s) for s in match.groups()]
                    break
            if not handler:
                #handler = ErrorHandler(self, request, 404)
                handler = self.settings.get('error_page')(self, request, 404)

        logging.debug("URL MATCH: ")
        logging.debug(handler.__class__)

        try:
            # apply extensions
            if (not isinstance(handler, ErrorHandler) and
                not isinstance(handler, StaticFileHandler)):
               handler = self._apply_extensions(handler)
            # In debug mode, re-compile templates and reload static files on every
            # request so you don't need to restart to see changes
            if self.settings.get("debug"):
                if getattr(RequestHandler, "_templates", None):
                    try:
                        map(lambda loader: loader.reset(),
                            RequestHandler._templates.values())
                    except AttributeError:
                        # jinja2 & mako template  has already a autoreload func
                        pass
                RequestHandler._static_hashes = {}
            handler._execute(transforms, *args, **kwargs)
        except HTTPErrorWrapper, e:
            if hasattr(handler, '_new_cookies'):
                cookies = handler._new_cookies
            else:
                cookies = None

            handler = self.settings.get('error_page')(self, request,
                e.status_code, e.log_message, e.format_exc)

            if cookies:
                logging.debug('HTTPErrorWrapper with cookies. ')
                logging.debug(cookies)
                handler._new_cookies = cookies
            handler.get()
        except HTTPError, e:
            if hasattr(handler, '_new_cookies'):
                cookies = handler._new_cookies
            else:
                cookies = None

            tb = traceback.format_exc().splitlines()
            handler = self.settings.get('error_page')(self, request,
                e.status_code, e.log_message, tb)

            if cookies:
                logging.debug('HTTPError with cookies. ')
                logging.debug(cookies)
                handler._new_cookies = cookies
            handler.get()
        except Exception, e:
            if hasattr(handler, '_new_cookies'):
                cookies = handler._new_cookies
            else:
                cookies = None

            tb = traceback.format_exc().splitlines()
            handler = self.settings.get('error_page')(self, request,
                500, e.message, tb)

            if cookies:
                logging.debug('Unknown exception with cookies. ')
                logging.debug(cookies)
                handler._new_cookies = cookies
            handler.get()
        logging.debug("Response headers: %s" % handler._headers)
        return handler

    def _load_template_engine(self):
        self.template_engine = TemplateEngineDelegate()

    def _load_extensions(self, extensions):
        if extensions is None:
            self.extensions = []
        else:
            self.extensions = extensions

    def _apply_extensions(self, handler):
        """Apply extensions to given handler
        """
        for extension in self.extensions:
            handler = extension(handler)
        return handler

    def _adjust_settings(self, settings):
        serve_type = settings.get('serve_type', 'tornado')
        if serve_type != 'wsgi':
            port = settings.get('port', 8888)
            define("port", default=port, help="run on the given port", type=int)

        default_host = settings.get('default_host', '')
        if not default_host:
            settings['default_host'] = ''

        if not settings.get('error_page'):
            settings['error_page'] = ErrorPage

        project_path = whirly.project.project_directory()
        project_name = whirly.project.project_name()
        static_path = settings.get('static_path', os.path.join(project_path,
            project_name, 'static'))
        settings['static_path'] = static_path

        return settings


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


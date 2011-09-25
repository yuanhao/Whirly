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

# Import dependencies
libs_dir = os.path.join(os.path.dirname(__file__), 'libs')
for d in os.listdir(libs_dir):
    target_dir = os.path.join(libs_dir, d)
    if os.path.isdir(target_dir):
        sys.path.append(target_dir)

from whirly.options import options
from whirly.options import enable_pretty_logging
from whirly import project


def run(settings_module):

    # Set project environment
    project.set_project_environment(settings_module)

    # prepare settings for application
    urls_module_name = options.urls_module
    __import__(urls_module_name)
    urls_module = sys.modules[urls_module_name]

    d  = settings_module.__dict__
    extensions_settings  = d.get('extensions')
    settings_data  = [d[s] for s in d if not (s.startswith('__') or
                                              s=='extensions')]
    logging.debug("Settings data: ")
    logging.debug(settings_data)
    settings = dict()
    for setting in settings_data:
        settings.update(setting)

    settings['error_page'] = urls_module.__dict__.get('error_page', None)
    handlers = urls_module.__dict__.get('routes', None)

    # Load extension classes 
    extensions = []
    for ext_module  in extensions_settings.keys():
        __import__(ext_module)
        ext_cls_list = extensions_settings[ext_module]
        for ext_cls in ext_cls_list:
            extensions.append(sys.modules[ext_module].__dict__[ext_cls]())

    log_level = settings.get('logging', 'info')
    # XXX
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

    serve_type = settings.get('serve_type', 'tornado')
    if serve_type == 'wsgi':
        from whirly.wsgi import WSGIApplication
        # import wsgiref.handlers
        from google.appengine.ext.webapp.util import run_wsgi_app

        application = WSGIApplication(
            handlers=handlers,
            extensions=extensions,
            **settings
        )
        # wsgiref.handlers.CGIHandler().run(application)
        run_wsgi_app(application)
    else:
        import tornado.httpserver
        import tornado.ioloop
        from whirly.web import Application

        enable_pretty_logging()

        # Create application
        application = Application(
            handlers=handlers,
            extensions=extensions,
            **settings
        )
        http_server = tornado.httpserver.HTTPServer(application)
        http_server.listen(options.port)
        logging.info("Server served at port %d" % options.port)
        tornado.ioloop.IOLoop.instance().start()


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


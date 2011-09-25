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


__all__ = ['TemplateEngineDelegate', 'TemplateEngineError']


import os
import sys
import logging

# load tornado template, default
import tornado.template

# try to load jinja2 template
try:
    import jinja2
except ImportError:
    pass

# try to load mako template
try:
    from mako.template import Template
    from mako.lookup import TemplateLookup
except ImportError:
    pass

import whirly.project
from whirly.web import RequestHandler
from whirly import helpers


class TemplateEngineError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class TemplateEngine(object):
    def __init__(self, template_path=None):
        if not template_path:
            frame = sys._getframe(0)
            f = frame.f_code.co_filename
            while frame.f_code.co_filename == f:
                frame = frame.f_back
            self.template_path = os.path.dirname(frame.f_code.co_filename)
        else:
            self.template_path = template_path

    def render_string(self, template_name, handler, **kw):
        not NotImplementedError



class TemplateEngineJinja2(TemplateEngine):
    def render_string(self, template_name, handler, **kwargs):
        logging.debug(self.template_path)
        if not getattr(RequestHandler, "_templates", None):
            RequestHandler._templates = {}
        if self.template_path not in RequestHandler._templates:
            RequestHandler._templates[self.template_path] = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.template_path))
        t = RequestHandler._templates[self.template_path].get_template(
            template_name)

        args = dict(
            handler=handler,
            request=handler.request,
            current_user=handler.current_user,
            locale=handler.locale,
            _=handler.locale.translate,
            static_url=handler.static_url,
            xsrf_form_html=handler.xsrf_form_html,
            reverse_url=handler.application.reverse_url,
            helpers=helpers
        )
        args.update(handler.ui)
        args.update(kwargs)
        return t.render(**args)


class TemplateEngineMako(TemplateEngine):
    def render_string(self, template_name, handler, **kwargs):
        logging.debug(self.template_path)
        project_path = whirly.project.project_directory()
        mako_module_directory = whirly.project.setting('template',
                                'mako_module_directory', '')

        if not os.path.exists(mako_module_directory):
            mako_module_directory = os.path.join(project_path,
                'data', 'mako')

        if not getattr(RequestHandler, "_templates", None):
            RequestHandler._templates = {}

        if self.template_path not in RequestHandler._templates:
            RequestHandler._templates[self.template_path] = TemplateLookup(
                directories=[self.template_path],
                module_directory=mako_module_directory,
                input_encoding='utf-8',
                output_encoding='utf-8',
                filesystem_checks=whirly.project.setting('application',
                    'debug', False)
            )

        t = RequestHandler._templates[self.template_path].get_template(template_name)
        args = dict(
            handler=handler,
            request=handler.request,
            current_user=handler.current_user,
            locale=handler.locale,
            _=handler.locale.translate,
            static_url=handler.static_url,
            xsrf_form_html=handler.xsrf_form_html,
            reverse_url=handler.application.reverse_url,
            helpers=helpers,
            lookup=RequestHandler._templates[self.template_path]
        )
        args.update(handler.ui)
        args.update(kwargs)
        return t.render(**args)


class TemplateEngineTornado(TemplateEngine):
    def render_string(self, template_name, handler, **kwargs):
        logging.debug(self.template_path)
        if not getattr(RequestHandler, "_templates", None):
            RequestHandler._templates = {}

        if self.template_path not in RequestHandler._templates:
            RequestHandler._templates[self.template_path] = tornado.template.Loader(
                self.template_path)

        t = RequestHandler._templates[self.template_path].load(template_name)

        args = dict(
            handler=handler,
            request=handler.request,
            current_user=handler.current_user,
            locale=handler.locale,
            _=handler.locale.translate,
            static_url=handler.static_url,
            xsrf_form_html=handler.xsrf_form_html,
            reverse_url=handler.application.reverse_url,
            helpers=helpers
        )
        args.update(handler.ui)
        args.update(kwargs)
        return t.generate(**args)


template_engine_cls_map = {
    'tornado': TemplateEngineTornado,
    'jinja2': TemplateEngineJinja2,
    'mako': TemplateEngineMako,
}


class TemplateEngineDelegateMeta(type):
    def __call__(cls, *args, **kw):
        project_path = whirly.project.project_directory()
        project_name = whirly.project.project_name()
        tmpl_type = whirly.project.setting('template', 'template_type',
                                              'tornado')
        tmpl_path = whirly.project.setting('template', 'template_path',
                        os.path.join(project_path, project_name, 'templates'))
        try:
            return template_engine_cls_map[tmpl_type](tmpl_path)
        except KeyError:
            raise TemplateEngineError("Unknown template engine type %s" %
                                      tmpl_type)


class TemplateEngineDelegate(object):
    """
    """
    __metaclass__ = TemplateEngineDelegateMeta

    def __init__(self):
        pass


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


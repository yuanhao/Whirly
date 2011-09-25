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


__all__ = ['Extension']


import re
import sys
import logging

from tornado import web as utils
from tornado.options import options

import whirly.project


class Extension(object):
    def __init__(self, name=None):
        self.name = name
        self.settings = whirly.project.extension_settings(self.name)
        # Do we need global settings here? XXX
        # Although it can be got from project module
        self.transform_classes = []
        self._check_required()

    def __call__(self, handler):
        handler = self.before(handler)
        handler = self.after(handler)
        return handler

    def append_transform(self, transform):
        if isinstance(transform, utils.OutputTransform):
            self.transform_classes.append(transform)
        else:
            pass

    def define_required(self, setting_name, helptext):
        if not hasattr(self, '_required_settings'):
            self._required_settings = {}
        if not helptext:
            helptext = ''
        self._required_settings[setting_name] = helptext

    def _check_required(self):
        if not hasattr(self, '_required_settings'):
            return

        missed = []
        for s in self._required_settings.keys():
            try:
                self.settings[s]
            except KeyError:
                missed.append(s)

        if missed:
            logging.error("Required settings missed for %s" % self.name)
            for k in missed:
                logging.info("%s: %s" % (k, self._required_settings.get(k, '')))
            sys.exit(1)

    def before(self, handler):
        return handler

    def after(self, handler):
        """apply a transform object to handler
        """
        for t in self.transform_classes:
            handler._transforms.append(t(handler.request))
        return handler


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


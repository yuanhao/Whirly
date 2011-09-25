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
import logging

from whirly.extensions.base import Extension


class TransformLoader(Extension):
    def __init__(self):
        super(TransformLoader, self).__init__('transforms')
        for module_name in self.settings.keys():
            __import__(module_name)
            transform_class_list = self.settings[t]
            for transform_class in transform_class_list:
                self.append_transform(sys.modules[t].__dict__[transform_class])
                logging.debug("Transforms loaded: %s.%s" % (t, transform_class))


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



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

from whirly.options import define, options


def import_project_helpers(locals_dict):
    helpers_module_string = '.'.join((project_name(), 'helpers'))
    import_module(helpers_module_string, locals_dict)


def import_module(module_name, locals_dict):
    try:
        __import__(module_name)
        module = sys.modules[module_name]
        for x in [m for m in module.__dict__.keys() if not m.startswith('__')]:
                locals_dict[x] = module.__dict__[x]
    except ImportError:
        raise


def extension_settings(extension_name):
    try:
        settings_module_name = options.settings_module
        __import__(settings_module_name)
        settings_module = sys.modules[settings_module_name]
        return settings_module.__dict__.get(extension_name, {})
    except AttributeError, ImportError:
        return {}


def setting(namespace, setting, default=None):
    try:
        settings_module_name = options.settings_module
        __import__(settings_module_name)
        settings_module = sys.modules[settings_module_name]
        return settings_module.__dict__[namespace].get(setting, default)
    except AttributeError, ImportError:
        return default


def project_directory():
    return options.project_directory


def project_name():
    return options.project_name


def set_project_environment(settings_mod):
    if '__init__.py' in settings_mod.__file__:
        path = os.path.dirname(settings_mod.__file__)
    else:
        path = settings_mod.__file__

    directory, settings_filename = os.path.split(path)
    if directory == os.curdir or not directory:
        directory = os.getcwd()

    project_name = os.path.basename(directory)
    settings_name = os.path.splitext(settings_filename)[0]
    project_directory = os.path.abspath(os.path.join(directory, os.path.pardir))

    if 'settings_module' not in options:
        define('project_directory', project_directory)
        define('project_name', project_name)
        define('settings_module', '%s.%s' % (project_name, settings_name))
        define('urls_module', '%s.%s' % (project_name, 'urls'))

    sys.path.append(project_directory)



### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:

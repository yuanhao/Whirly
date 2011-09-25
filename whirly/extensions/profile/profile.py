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
import time
import logging
import cProfile
import pstats

from whirly import project
from whirly.libs.decorator import decorator



__all__ = ['profile']


def _get_log_path():
    path = project.setting('profile', 'profile_log_path')
    if not path:
        prj_path = project.project_directory()
        path = os.path.join(prj_path, 'data')
    path = os.path.join(path, 'profile')
    if not os.path.exists(path):
        os.makedirs(path)
    logging.debug('Profile store path: %s' % path)
    return path


HOSTING_TYPE = project.setting('application', 'serve_type')


if HOSTING_TYPE == 'wsgi':
    logging.info("Application running on google appengine. Profile "
                 "function disabled")
    PROFILE_LOG_PATH = None
else:
    PROFILE_LOG_PATH = _get_log_path()


def _make_profile_name(func):
    cls = None
    if hasattr(func, 'im_func'):
        cls = func.im_class
        func = func.im_func
        name = func.__name__
    else:
        name = func.__name__

    if cls:
        return '%s-%s-%s' % (cls.__module__.replace('.', '_'),
                             cls.__name__, name)
    else:
        return '%s-%s' % (func.__module__.replace('.', '_'),
                          name)


def profile(log_name=None):
    n = log_name
    is_debug = project.setting('application', 'debug', False)
    def prof(func, *args, **kwargs):
        if HOSTING_TYPE == 'google_appengine':
            return func(*args, **kwargs)

        if not n:
            log_name  = _make_profile_name(func)
        else:
            log_name = n
        logfile = os.path.join(PROFILE_LOG_PATH, log_name)
        (base, ext) = os.path.splitext(logfile)
        if not ext:
            ext = '.cprof'
        base = "%s-%s" % (base, time.strftime("%Y%m%dT%H%M%S", time.gmtime()))
        full_log_file = base + ext
        _locals = locals()
        cProfile.runctx("func(*args, **kwargs)", globals(), _locals,
                        full_log_file)
        if is_debug:
            pstats.Stats(full_log_file).strip_dirs().sort_stats('time').print_stats(20)
        return
    return decorator(prof)


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



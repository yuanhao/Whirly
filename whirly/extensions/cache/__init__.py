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
import inspect
import functools

from whirly import project
from whirly import utils


__all__ = ['whirly_cache', 'WC', 'cache', 'nocache']


default_timeout = project.setting('cache', 'default_timeout', 300)


def _get_cache_class():
    _cache_settings = project.extension_settings('cache')

    _cache_module_string = _cache_settings['extension'][0]
    _cls = _cache_settings['extension'][1]

    __import__(_cache_module_string)
    cache_module = sys.modules[_cache_module_string]
    return cache_module.__dict__[_cls]


whirly_cache = WC = _get_cache_class()(default_timeout)()


def _make_cache_key(func, key_dict, self):
    cls = None
    if hasattr(func, 'im_func'):
        cls = func.im_class
        func = func.im_func
        cache_key = func.__name__
    else:
        cache_key = func.__name__

    if key_dict:
        cache_key += "_" + "_".join(["%s_%s" % (k, v) for k, v in
                                     key_dict.iteritems()])
    if not cls and self:
        cls = getattr(self, '__class__', None)
    if cls:
        return '%s_%s_%s' % (cls.__module__.replace('.', '_'), cls.__name__,
                             cache_key)
    else:
        return '%s_%s' % (func.__module__.replace('.', '_'), cache_key)


def _make_dict_from_args(func, args):
    dict_ = {}
    for i, arg in enumerate(inspect.getargspec(func)[0]):
        if arg != 'handler':
            dict_[arg] = args[i]
    return dict_


def _wrapper(f, cache_key, timeout):
    @functools.wraps(f)
    def setcache(*args, **kwargs):
        chunk = args[0]
        WC.set(cache_key, chunk, timeout)
        return f(*args, **kwargs)
    return setcache


class cache(object):
    def __init__(self, timeout=None, with_query_args=False):
        self.timeout = timeout or project.setting('cache', 'default_timeout', 300)
        self.anonymous_only = project.setting('cache', 'anonymous_only', False)
        self.with_query_args = with_query_args

    def __call__(self, func):
        def _process(instance, *args, **kwargs):
            if self.anonymous_only:
                if instance.user.is_authenticated():
                    return func(instance, *args, **kwargs)

            cache_key_dict = kwargs.copy()
            cache_key_dict.update(_make_dict_from_args(func, args))
            if self.with_query_args:
                cache_key_dict.update(instance.request.arguments)
            cache_key = _make_cache_key(func, cache_key_dict, instance)
            data = WC.get(cache_key)
            logging.debug("Cache key: %s" % cache_key)
            if not data:
                logging.debug("Cache not exist. Need to regenerate. ")
                instance.finish = _wrapper(instance.finish, cache_key, self.timeout)
                return func(instance, *args, **kwargs)
            return instance.finish(data)
        return _process


class nocache(object):
    def __call__(self, func):
        def _set_no_cache(handler, *args, **kwargs):
            handler._headers.update(utils.no_cache_headers())
            return func(handler, *args, **kwargs)
        return _set_no_cache


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



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



import re
import sys
import time
import datetime
import threading
from UserDict import DictMixin


__all__ = ['odict', 'AttrDict', 'ThreadedDict', 'timedelta', 'MultiDict']


class MultiDict(dict):
    def getlist(self, key):
        if isinstance(self[key], list):
            return self[key]
        else:
            return []


class odict(DictMixin):
    def __init__(self, data=None, **kwdata):
        self._keys = []
        self._data = {}
        if data is not None:
            if hasattr(data, 'items'):
                items = data.items()
            else:
                items = list(data)
            for i in xrange(len(items)):
                length = len(items[i])
                if length != 2:
                    raise ValueError('dictionary update sequence element '
                        '#%d has length %d; 2 is required' % (i, length))
                self._keys.append(items[i][0])
                self._data[items[i][0]] = items[i][1]
        if kwdata:
            self._merge_keys(kwdata.iterkeys())
            self.update(kwdata)

    def __repr__(self):
        result = []
        for key in self._keys:
            result.append('(%s, %s)' % (repr(key), repr(self._data[key])))
        return ''.join(['OrderedDict', '([', ', '.join(result), '])'])

    def _merge_keys(self, keys):
        self._keys.extend(keys)
        newkeys = {}
        self._keys = [newkeys.setdefault(x, x) for x in self._keys
            if x not in newkeys]

    def update(self, data):
        if data is not None:
            if hasattr(data, 'iterkeys'):
                self._merge_keys(data.iterkeys())
            else:
                self._merge_keys(data.keys())
            self._data.update(data)

    def __setitem__(self, key, value):
        if key not in self._data:
            self._keys.append(key)
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]
        self._keys.remove(key)

    def __iter__(self):
        for key in self._keys:
            yield key

    def keys(self):
        return list(self._keys)

    def copy(self):
        copyDict = odict()
        copyDict._data = self._data.copy()
        copyDict._keys = self._keys[:]
        return copyDict


class MultiDict(dict):
    def getlist(self, key):
        if isinstance(self[key], list):
            return self[key]
        else:
            return []


class AttrDict(dict):
    """ Makes a dict can be accessed by attribute

    >>> d = AttrDict(a=1, b=2, c=3)
    >>> d.a
    1
    >>> d.b
    2
    >>> d.c
    3
    >>> d['a']
    1
    >>> d['b']
    2
    >>> d['c']
    3
    >>> del d.a
    >>> d.a
    Traceback (most recent call last):
        ...
    AttributeError: 'a'

    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, error:
            raise AttributeError, error

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, error:
            raise AttributeError, error

    def __repr__(self):
        return '<AttrDict ' + dict.__repr__(self) + '>'


class ThreadedDict:
    """Thread local dict

    >>> d = ThreadedDict()
    >>> d.x = 1
    >>> d.x
    1
    >>> import threading
    >>> def f(): d.x = 2
    ...
    >>> t = threading.Thread(target=f)
    >>> t.start()
    >>> t.join()
    >>> d.x
    1

    """
    def __getattr__(self, key):
        return getattr(self._getd(), key)

    def __setattr__(self, key, value):
        return setattr(self._getd(), key, value)

    def __delattr(self, key):
        return delattr(self._getd(), key)

    def __hash__(self):
        return id(self)

    def _getd(self):
        t = threading.currentThread()
        if not hasattr(t, '_d'):
            # thread local storage
            t._d = {}

        if self not in t._d:
            t._d[self] = AttrDict()
        return t._d[self]

    def get(self, key, default=None):
        try:
            return getattr(self._getd(), key)
        except AttributeError:
            return default


_timedelta_re = re.compile(r"(?P<amount>\d+)(?P<unit>[w|d|h|m|s|ms])")

def timedelta(expr):
    """ Returns datetime.timedelta object for the given expression

    The format of expr looks like '24d', '24' is the amount, 'd' is time unit
    'd' is for day, 'w' is for week, 'h' is for hour, 'm' is for minute, 's' is
    for second, 'ms' is for microsecond

        >>> expr = "5d"
        >>> x = timedelta(expr)
        >>> isinstance(x, datetime.timedelta)
        True
        >>> x.days
        5
        >>> x.seconds
        0
        >>> expr = "2W"
        >>> x = timedelta(expr)
        >>> isinstance(x, datetime.timedelta)
        True
        >>> x.days
        14
        >>> expr = "2d2h 2s"
        >>> x = timedelta(expr)
        >>> x.days
        2
        >>> x.seconds
        7202
        >>> expr = "2d 3d 4d"
        >>> x = timedelta(expr)
        >>> x.days
        4

    """

    _unit_map = {
        'w': 'weeks',
        'd': 'days',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds',
        'ms': 'microseconds',
    }
    matches = _timedelta_re.findall(expr.lower())

    if matches:
        kw = {}
        for amount, unit in matches:
            kw.update({_unit_map[unit]: int(amount)})
        return datetime.timedelta(**kw)
    else:
        raise


def sqlify(obj):
    """Convert `obj` to its proper SQL version
    >>> sqlify(None)
    'NULL'
    >>> sqlify(True)
    "'t'"
    >>> sqlify(3)
    "'3'"
    """
    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if isinstance(obj, unicode):
            obj = obj.encode('utf8')
        return repr(obj)


def no_cache_headers():
    return {
        'Expires': 'Thu, 10 Jul 1980 05:45:00 GMT',
        'Last-Modified': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime()),
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Cache-Control': 'post-check=0, pre-check=0',
        'Pragma': 'no-cache'
    }


if __name__ == "__main__":
    import doctest
    doctest.testmod()


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


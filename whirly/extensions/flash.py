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


from whirly import utils
from whirly.extensions.base import Extension


class FlashMessage(object):
    def __init__(self, handler):
        self.__dict__['handler'] = handler
        self.handler._headers.update(utils.no_cache_headers())
        if self.handler.get_secure_cookie("flash_message"):
            self.message = self.handler.get_secure_cookie("flash_message")
            self.handler.clear_cookie("flash_message")
        else:
            self.message = None
        settings = handler.application.settings
        self.__dict__['cookie_domain'] = settings.get('cookie_domain')
        self.__dict__['cookie_path'] = settings.get('cookie_path', '/')
        self.__dict__['cookie_expires_days'] = None

    def __setattr__(self, attr, value):
        if attr != 'message':
            raise ValueError("You can only set the 'message' attribute. ")
        super(FlashMessage, self).__setattr__(attr, value)

    def __call__(self, message):
        self.message = message
        self.handler.set_secure_cookie(
            'flash_message',
            message,
            domain=self.cookie_domain,
            path=self.cookie_path,
            expires_days=self.cookie_expires_days
        )


class Flash(Extension):
    def __init__(self):
        super(Flash, self).__init__('flash')

    def before(self, handler):
        handler.flash = FlashMessage(handler)
        return handler



### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:



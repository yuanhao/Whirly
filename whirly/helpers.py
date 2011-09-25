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



# import markdown as _markdown

# markdown = _markdown.Markdown(extensions=['extra', 'toc', 'wikilinks',
                              # 'mdx_video'], safe_mode=False)


from tornado import escape
from tornado.web import addslash, removeslash

from whirly import project
project.import_project_helpers(locals())


### EOF ###
# vim:smarttab:sts=4:sw=4:et:ai:tw=80:


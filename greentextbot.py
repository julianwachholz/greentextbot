# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import logging

from reddit_bot import RedditReplyBot


logger = logging.getLogger(__name__)


class GreentextBot(RedditReplyBot):

    VERSION = (1, 0, 0)

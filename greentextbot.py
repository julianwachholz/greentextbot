# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re
import logging

from reddit_bot import RedditSubmissionBot
from greentext import Greentext


logger = logging.getLogger(__name__)


REPLY_INFO = '\n---\n[^(Bitch I\'m a bot)](#info "v{}")'


class GreentextBot(RedditSubmissionBot):

    VERSION = (0, 0, 1)

    VALID_DOMAINS = [
        'imgur.com',
        'i.imgur.com',
    ]

    def bot_start(self):
        super(GreentextBot, self).bot_start()
        self.reply_info = REPLY_INFO.format('.'.join(map(str, self.VERSION)))

    def is_valid_submission(self, submission):
        return all([
            not submission.is_self,
            not submission.stickied,
            submission.distinguished != 'moderator',
            submission.domain in self.VALID_DOMAINS,
        ])

    def reply_submission(self, submission):
        logger.info('Submission: {} {:.40}'.format(submission.id, submission.title))
        import time
        time.sleep(5.0)

        url = self.get_image_url(submission)
        if not url:
            return False

        g = Greentext.from_url(url)

        if not g.has_greentext():
            return False

        reply_text = g.get_greentext()
        submission.reply(reply_text)
        return True

    def get_image_url(self, submission):
        url = submission.url

        if submission.domain == 'i.imgur.com':
            return url

        if re.match(r'https?://imgur\.com/a/', url):
            return False

        return '{}.png'.format(url)

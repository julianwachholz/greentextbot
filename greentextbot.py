# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re
import logging
import time

from praw.errors import RateLimitExceeded
from praw.objects import Submission

from reddit_bot import RedditSubmissionBot, RedditMessageBot
from greentext import Greentext


logger = logging.getLogger(__name__)


REPLY_INFO = '\n---\n[^(Bitch I\'m a bot)](#info "v{}")'


class GreentextBot(RedditSubmissionBot, RedditMessageBot):

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
        url = self.get_image_url(submission)
        if not url:
            return False

        g = Greentext.from_url(url)

        if not g.has_greentext():
            return False

        logger.info('Replying to {}'.format(submission.id))
        reply_text = g.get_greentext()
        reply_text += self.reply_info
        return submission.add_comment(reply_text)

    def get_image_url(self, submission):
        url = submission.url

        if submission.domain == 'i.imgur.com':
            return url

        if re.match(r'https?://imgur\.com/a/', url):
            return False

        return '{}.png'.format(url)

    def on_admin_message(self, message):
        if message.subject != 'check':
            return

        checked = []
        submission_ids = map(lambda s: s.strip(), message.body.split('\n'))

        for submission_id in submission_ids:
            submission = self.r.get_info(thing_id='t3_{}'.format(submission_id))
            if isinstance(submission, Submission):
                logger.info('Checking {!r} - {:.40}'.format(
                            submission_id, submission.title))
                if self.is_valid_submission(submission):
                    try:
                        reply = self.reply_submission(submission)
                    except RateLimitExceeded as e:
                        logger.info('RateLimitExceeded: wait {}s'.format(e.sleep_time))
                        time.sleep(e.sleep_time + 1)
                        reply = self.reply_submission(submission)
                    if reply:
                        logger.info('Replied, sleeping {} seconds.'.format(
                                    self.settings['wait_after_reply']))
                        time.sleep(self.settings['wait_after_reply'])
                else:
                    reply = None
                checked.append((submission, reply))
            else:
                logger.warn('Got something other than a submission: {!r} - {!r}'.format(
                            submission_id, submission))

        text = "Checked the following submissions:\n\n"
        for submission, reply in checked:
            text += '\n- [{:.30}]({}): '.format(submission.title, submission.permalink)
            if reply:
                text += '[**my reply**]({})'.format(reply.permalink)
            else:
                text += '*not replied*'

        if not checked:
            text += 'No submissions checked.'

        text += '\n'
        message.reply(text)
        message.mark_as_read()

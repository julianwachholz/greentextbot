# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import re
import logging
import time

from praw.errors import RateLimitExceeded
from praw.objects import Submission, Comment

from reddit_bot import RedditSubmissionBot, RedditMessageBot
from greentext import Greentext


logger = logging.getLogger(__name__)


REPLY_INFO = ('\n\n---\n[^(I\'m a bot)](/message/compose/?to=_greentext_'
              '&subject=feedback "v{} - {{}}")')


class GreentextBot(RedditSubmissionBot, RedditMessageBot):

    VERSION = (0, 2, 0)

    VALID_DOMAINS = [
        'imgur.com',
        'i.imgur.com',
    ]

    MAX_LENGTH = 10000

    def bot_start(self):
        super(GreentextBot, self).bot_start()
        self.done = []
        self.reply_info = REPLY_INFO.format('.'.join(map(str, self.VERSION)))

    def is_valid_submission(self, submission):
        return all([
            not submission.is_self,
            not submission.stickied,
            submission.distinguished != 'moderator',
            submission.domain in self.VALID_DOMAINS,
            submission.id not in self.done,
        ])

    def reply_submission(self, submission):
        logger.info('Submission {!r} - {:.40}'.format(
                    submission.id, submission.title))
        url = self.get_image_url(submission)
        if not url:
            return False

        g = Greentext.from_url(url)

        if not g.has_greentext():
            return False

        logger.info('Replying to {}'.format(submission.id))
        self.append_done(submission.id)
        return self._do_reply(submission, g)

    def _do_reply(self, submission, g):
        """Reply to the submission with reply_text.

        Split into multiple comments when we found more
        than one post.

        Returns the first comment created.

        """
        reply_text = g.get_greentext()

        if len(reply_text) > self.MAX_LENGTH / 10:
            posts = map(lambda s: s.strip(), reply_text.split('---'))
        else:
            posts = [reply_text]

        replies = []
        reply_info = self.reply_info.format(g.get_times())
        comment_func = submission.add_comment

        for post in posts:
            if len(post + reply_info) > self.MAX_LENGTH:
                return False

            comment = comment_func(post + reply_info)
            comment_func = comment.reply
            replies.append(comment)

        return replies[0]

    def append_done(self, submission_id):
        self.done.append(submission_id)
        if len(self.done) > 100:
            self.done = self.done[1:]

    def get_image_url(self, submission):
        url = submission.url

        if submission.domain == 'i.imgur.com':
            return url

        # does not match album or imgur-subreddit links
        match = re.match(r'^https?://imgur\.com/([a-z0-9]{6,9})$', url, flags=re.I)
        if not match:
            return False
        return 'http://i.imgur.com/{}.png'.format(match.group(1))

    def on_subreddit_message(self, subreddit, message):
        if message.subject.lower() != 'check':
            return
        self._manual_check(message, subreddit)

    def on_admin_message(self, message):
        if message.subject.lower() != 'check':
            return
        self._manual_check(message)

    def _manual_check(self, message, subreddit=None):
        checked = []
        submission_ids = map(lambda s: s.strip(), message.body.split('\n'))

        for submission_id in submission_ids:
            submission = self.r.get_info(thing_id='t3_{}'.format(submission_id))
            if isinstance(submission, Submission):
                if subreddit and submission.subreddit.display_name != subreddit:
                    reply = 'Submission not in your sub'
                elif self.is_valid_submission(submission):
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
                logger.warning('Got something other than a submission: {!r} - {!r}'.format(
                            submission_id, submission))

        text = "Checked the following submissions:\n\n"
        for submission, reply in checked:
            text += '\n- [{:.30}]({}): '.format(submission.title, submission.permalink)
            if isinstance(reply, Comment):
                text += '[**my reply**]({})'.format(reply.permalink)
            elif reply:
                text += reply
            else:
                text += '*not replied*'

        if not checked:
            text += 'No submissions checked.'

        text += '\n'
        message.reply(text)
        message.mark_as_read()

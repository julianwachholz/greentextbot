# -*- encoding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import sys
import logging
import re
import requests
import time

from requests.exceptions import ConnectionError, MissingSchema

from StringIO import StringIO
from PIL import Image, ImageEnhance
from pytesseract import image_to_string


logger = logging.getLogger(__name__)


class Greentext(object):
    IMG_RESIZE_FACTOR = 4
    IMG_CONTRAST_FACTOR = 2.0

    MIN_LINES = 4
    RATIO = 0.4

    def __init__(self, image=None, start_time=None, download_time=None):
        self.image = image
        self.raw_text = None
        self.greentext = None

        self.start_time = start_time
        self.download_time = download_time
        self.enhance_time = 0
        self.parse_time = 0
        self.total_time = 0

        if self.image:
            self._enhance_image()
            self._parse_greentext()

        if self.start_time:
            self.total_time = time.time() - self.start_time

    @classmethod
    def from_url(cls, url):
        logger.debug('Trying to fetch {!r}'.format(url))
        start_time = time.time()
        try:
            r = requests.get(url)
            image = Image.open(StringIO(r.content))
            logger.debug('Downloaded image: {!r}'.format(image))
            download_time = time.time() - start_time
            return cls(image, start_time, download_time)
        except (MissingSchema, ConnectionError):
            logger.warn('Failed fetching URL {!r}'.format(url))
            return cls()

    @classmethod
    def from_file(cls, filename):
        logger.debug('Trying to open {!r}'.format(filename))
        try:
            image = Image.open(filename)
            return cls(image)
        except IOError:
            logger.error('No such file {!r}'.format(filename))
            return cls()

    def is_valid(self):
        return self.image is not None

    def has_greentext(self):
        return self.greentext is not None

    def get_greentext(self):
        return self.greentext

    def get_times(self):
        info = '{total:.3}s (dl: {download:.4}/prep: {enhance:.4}/ocr: {parse:.4})'
        return info.format(
            total=self.total_time,
            download=self.download_time,
            enhance=self.enhance_time,
            parse=self.parse_time
        )

    def _enhance_image(self):
        start_time = time.time()

        new_size = (p * Greentext.IMG_RESIZE_FACTOR for p in self.image.size)
        image = self.image.resize(new_size, resample=Image.BILINEAR)
        image = image.convert('L')  # grayscale
        max_contrast = ImageEnhance.Contrast(image)
        image = max_contrast.enhance(Greentext.IMG_CONTRAST_FACTOR)

        self.enhance_time = time.time() - start_time
        logger.info('Enhanced image in {!r}s'.format(self.enhance_time))
        self.image = image

    def _parse_greentext(self):
        start_time = time.time()
        self.raw_text = image_to_string(self.image).decode('utf-8')
        self.parse_time = time.time() - start_time
        logger.info('OCR took {!r}s'.format(self.parse_time))
        greentext = self._format_greentext(self.raw_text)

        if self._verify_greentext(greentext):
            self.greentext = greentext

    def _format_greentext(self, raw_text):
        """Prepare and format text as markdown."""
        # replace common alternative '>' detections
        for arrow in [':=-', '2:-', 'r=-', 'I=-']:
            raw_text = raw_text.replace(arrow, '>')
        lines = []

        previous_empty = False
        previous_quote = False

        for line in raw_text.split('\n'):
            if self._is_post_separator(line):
                if len(lines):
                    lines.append('')
                    lines.append('---')
                elif self._get_topic(line):
                    lines.append(self._get_topic(line))
                continue

            line = re.sub(r'^([^\w]*?>|:)', '>', line, flags=re.M)

            if not line:
                previous_empty = True
            elif line[0] == '>':
                if not previous_empty and not previous_quote:
                    lines.append('')

                prepend = '\\' if previous_quote else ''
                lines.append(prepend + line)
                previous_quote = True
                previous_empty = False
            elif previous_quote and not previous_empty:
                lines[-1] += ' ' + line
                previous_empty = False
            else:
                lines.append('')
                lines.append(line)
                previous_quote = False
                previous_empty = False

        return '  \n'.join('\n'.join(lines).strip('-').split('\n'))

    def _is_post_separator(self, line):
        return any([
            'Anonymous' in line,
            re.match(r'\d\d/\d\d/\d\d', line),
            re.match(r'No\. ?\d{4,}', line),
        ])

    def _get_topic(self, line):
        for part in line.split('\n'):
            if self._is_post_separator(part):
                topic = part.split('Anonymous')[0]
                if len(topic) > 6:
                    return '**{}**'.format(topic.strip())

    def _verify_greentext(self, greentext):
        """Make sure we have an actual greentext post."""
        lines = greentext.split('\n')
        try:
            assert len(lines) > Greentext.MIN_LINES, (
                'Not enough lines (min: {}, got: {})'.format(Greentext.MIN_LINES, len(lines)))

            ratio_filter = lambda l: l.startswith('>') or l.startswith('\\>')
            ratio = len(filter(ratio_filter, lines)) / len(lines)
            assert ratio > Greentext.RATIO, (
                'Quote ratio too low: (min: {}, got: {})'.format(Greentext.RATIO, ratio))
        except AssertionError as e:
            logger.warn('Invalid greentext: {}'.format(e))
            return False
        return True


if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    if len(sys.argv) < 2:
        sys.stderr.write('Usage: {} <file>\n'.format(sys.argv[0]))
        sys.exit(1)

    g = Greentext.from_file(sys.argv[1])

    if g.has_greentext():
        print('')
        print(g.get_greentext())
    else:
        print("No greentext found.")

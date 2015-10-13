#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys
import logging
import re

from PIL import Image, ImageOps  # noqa
# from textblob import TextBlob  # noqa
from pytesseract import image_to_string


logger = logging.getLogger(__name__)

RESIZE_FACTOR = 4


def main(file, expected=None):
    image = Image.open(file)
    new_size = (p * RESIZE_FACTOR for p in image.size)
    image = image.resize(new_size, resample=Image.BILINEAR)
    image = image.convert('L')  # grayscale
    # image = ImageOps.invert(image)
    # image = image.filter(ImageFilter.SMOOTH_MORE)
    text = prettify(image_to_string(image).decode('utf-8'))

    if expected is None:
        print(text)
    else:
        print('Checking similarity to expected result.')
        from difflib import SequenceMatcher
        seq = SequenceMatcher(None, text, expected)

        print('quick_ratio: {!r}'.format(seq.quick_ratio()))
        print('real_quick_ratio: {!r}'.format(seq.real_quick_ratio()))
        print('ratio: {!r}'.format(seq.ratio()))


def is_post_separator(line):
    return any([
        'Anonymous' in line,
        re.match(r'\d\d/\d\d/\d\d', line),
        re.match(r'No\. ?\d{4,}', line),
    ])


def get_topic(line):
    for part in line.split('\n'):
        if is_post_separator(part):
            topic = part.split('Anonymous')[0]
            if len(topic) > 6:
                return '**{}**'.format(topic)


def prettify(text):
    """Prepare for markdown."""
    # replace common alternative '>' detections
    text = text.replace(':=-', '>').replace('2:-', '>')
    lines = []

    for line in text.split('\n\n'):
        if is_post_separator(line):
            if len(lines):
                lines.append('---')
            elif get_topic(line):
                lines.append(get_topic(line))
            continue

        if re.match(r'^[\W]*>', line, flags=re.M):
            line = re.sub(r'^([^\w]>)', '>', line, flags=re.M)

        if len(lines) and not line[0] == '>' \
                or len(lines) > 0 and line[0] == '>' and lines[-1][0] != '>':
            lines.append('')

        lines.append(line)
    return '  \n'.join('\n'.join(lines).strip('-').split('\n'))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: {} <file> [expected.txt]\n'.format(sys.argv[0]))

    if len(sys.argv) == 3:
        with open(sys.argv[2]) as f:
            expected = f.read().decode('utf-8')
    else:
        expected = None
    main(sys.argv[1], expected)

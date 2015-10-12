#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys

from PIL import Image
from textblob import TextBlob
from pytesseract import image_to_string


RESIZE_FACTOR = 2


def main(file):
    image = Image.open(file)
    image = image.resize(p * RESIZE_FACTOR for p in image.size)
    image = image.convert('L')  # grayscale
    text =  image_to_string(image)

    prettify(text.decode('utf-8'))


def prettify(text):
    lines = []
    for line in text.split('\n>'):
        lines.append(' '.join(line.split('\n')))
    print('>' + '\n>'.join(lines))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: {} <file>\n'.format(sys.argv[0]))

    main(sys.argv[1])

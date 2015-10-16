# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from difflib import SequenceMatcher
import pytest

from greentext import Greentext


@pytest.mark.parametrize('testfile', [
    'chan',
    # 'heist',
    # 'drugs',
])
def test_greentext(testfile):
    with open('test_files/{}.txt'.format(testfile), 'r') as f:
        expected = f.read()

    image = 'test_files/{}.png'.format(testfile)

    g = Greentext.from_file(image)

    assert g.has_greentext(), 'No greetext detected in {}'.format(testfile)

    matcher = SequenceMatcher(a=g.get_greentext(), b=expected)
    longest_match = matcher.find_longest_match(0, len(g.get_greentext()), 0, len(expected))

    print g.get_greentext()

    # print len(g.get_greentext()), len(expected), longest_match
    assert longest_match.size * 10 > len(expected)
    assert matcher.ratio() > 0.9

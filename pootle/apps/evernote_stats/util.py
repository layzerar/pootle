#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2013 Evernote Corporation

from __future__ import unicode_literals

import re
from difflib import SequenceMatcher


ADDED, REMOVED = range(2)

remove = re.compile("[\.]+", re.U) # dots

delimiters = re.compile("[\W]+", re.U) # anything except a-z, A-Z and _
delimiters_begin = re.compile("^[\W]+", re.U) # anything except a-z, A-Z and _
delimiters_end = re.compile("[\W]+$", re.U) # anything except a-z, A-Z and _

english_date = re.compile(
    "(^|\W)(January|February|March|April|May|June|July|August|September|"
    "October|November|December)\s+\d{1,2},\s+(?:\d{2})?\d{2}(\W|$)",
    re.U
)


def diff_stat(old, new):
    result = [0, 0]  # [ADDED, REMOVED]

    def insert(i1, i2, j1, j2):
        result[ADDED] += j2 - j1

    def delete(i1, i2, j1, j2):
        result[REMOVED] += i2 - i1

    def update(i1, i2, j1, j2):
        result[REMOVED] += i2 - i1
        result[ADDED] += j2 - j1

    opcode_handler = {
        'insert': insert,
        'delete': delete,
        'replace': update,
        'equal': None,
    }

    sm = SequenceMatcher(None, old, new)

    for (tag, i1, i2, j1, j2) in sm.get_opcodes():
        f = opcode_handler[tag]
        if callable(f):
            f(i1, i2, j1, j2)

    return result


def find_placeholders(aref, regex, cls=''):
    # regex is compiled re object with pattern surrounded by "()"
    i = 0;
    while i < len(aref):
        chunk = aref[i];

        if not chunk['translate']:
            i += 1;
        else:
            subchunks = regex.split(chunk['string']);
            a = [];
            translate = False;

            for subchunk in  subchunks:
                translate = not translate;
                a.append({
                    'translate': translate,
                    'string': subchunk,
                    'class': cls
                });

            aref[i:i+1] = a;
            i += len(a);


def wordcount(string):
    string = re.sub('\n', '{\\n}', string)

    chunks = [{
        'translate': 1,
        'string': u'%s' % string,
    }]

    # FIXME: provide line continuations to fit lines below 80 chars

    # Escaped XML tags (used in some strings)
    find_placeholders(chunks, re.compile('(&lt;\/?[\w]+.*?>)', re.U))
    # XML tags
    find_placeholders(chunks, re.compile('(<\/?[\w]+.*?>)', re.U))
    # Java format and it's escaped version
    find_placeholders(chunks, re.compile('(\\\{\d+\\\}|\{\d+\})', re.U)
    # Template format
    find_placeholders(chunks, re.compile('(\$\{[\w\.\:]+\})', re.U))
    # Android format
    find_placeholders(chunks, re.compile('(%\d\$\w)', re.U))
    # sprintf
    find_placeholders(chunks, re.compile('(%[\d]*(?:.\d+)*(?:h|l|I|I32|I64)*[cdiouxefgns])', re.U))
    # Objective C style placeholders
    find_placeholders(chunks, re.compile('(%@)', re.U))
    # Dollar sign placeholders
    find_placeholders(chunks, re.compile('(\$[\w\d]+?\$)', re.U))
    # Percent sign placeholders
    find_placeholders(chunks, re.compile('(\%[\w\d]+?\%)', re.U))
    # '{\n}' newline marker
    find_placeholders(chunks, re.compile('(\{\\\n\})', re.U))
    # Escaping sequences (\n, \r, \t)
    find_placeholders(chunks, re.compile('(\\\+[rnt])', re.U))
    # XML entities
    find_placeholders(chunks, re.compile('(&#\d+;|&\w+;)', re.U))
    # Product names
    find_placeholders(chunks, re.compile('(Evernote International|Evernote Food|Evernote Hello|Evernote Clearly|Evernote Business|Skitch|Evernote®?|Food|^Hello$|Clearly)', re.U))
    # Shortcuts
    find_placeholders(chunks, re.compile('(Ctrl\+\w$|Shift\+\w$|Alt\+\w$)', re.U))
    # Shortcut modifiers
    find_placeholders(chunks, re.compile('(Ctrl\+$|Shift\+$|Alt\+$)', re.U))
    # Surrounding quotes (including ones around placeholders)
    #find_placeholders($chunks, re.compile('(^["\']+|["\']+$)', re.U))
    # End punctuation after (or between) placeholders
    #find_placeholders($chunks, re.compile('(^\.$)', re.U))

    # Find patterns that are not counted as words in Trados
    # Hanging symbols (excluding a-z, _ and &)
    find_placeholders(chunks, re.compile('(^[^\w\&]\s|\s[^\w\&]\s|\s[^\w\&]$|^[^\w\&]$)', re.U), 'dont-count')

    return _count_words(chunks)


def _count_words(aref):
    # These rules are based on observed Trados 2007 word calculation behavior
    n = 0

    for chunk in aref:
        if chunk['translate']:
            s = chunk['string']
            # Replace the date with just the month name (i.e. count as a single word)
            s = english_date.sub('\g<1>\g<2>\g<3>', s)

            s = remove.sub('', s)
            s = delimiters_begin.sub('', s)
            s = delimiters_end.sub('', s)

            a = delimiters.split(s);

            if len(a) > 1 and a[-1] == '':
                a.pop()

            if len(a) == 1 and a[0] == '':
                a.pop()

            n += len(a);

    return n

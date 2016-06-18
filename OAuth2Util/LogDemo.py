#!/usr/bin/env python

import praw
import OAuth2Util
import logging


log = OAuth2Util.get_logger()
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())

r = praw.Reddit("OAuth2Util Demo by /u/SmBe19")
o = OAuth2Util.OAuth2Util(r)

o.refresh(force=True)

print("Hi, {0}, you have {1} comment karma!".format(
    r.get_me().name, r.get_me().comment_karma))

#!/usr/bin/env python

import praw
import OAuth2Util
import time

r = praw.Reddit("OAuth2Util Demo by /u/SmBe19")
o = OAuth2Util.OAuth2Util(r, print_log=True)

sub = r.get_subreddit("askreddit")

while True:
    o.refresh()
    sub.refresh()

    print("---")
    for post in sub.get_comments(limit=10):
        print(post.author.name)

    time.sleep(120)

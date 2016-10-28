#!/usr/bin/env python3
#
# Copyright 2016 Sarah Sharp <sharp@otter.technology>
#
# This program creats statistics and graphs from
# github interactions stored in the format:
# 
# .
# |-- github owner
#     |-- repository name
#         |-- issue-<id>
#         |   |-- issue-<id>.json
#         |   |-- comment-<id>.json
#         |   |-- pr-<id>.json
#         |   |-- pr-comment-<id>.json
#
# It also uses the following files:
#  - first-interactions.txt
#  - reporters.txt
#  - responders.txt
#  - submitters.txt
#  - contributors.txt
#  - reviewers.txt
#  - mergers.txt

import os
import re
import statistics
import argparse
from datetime import datetime, timedelta
from plotly.offline import download_plotlyjs, init_notebook_mode, iplot, offline
from plotly.graph_objs import *

# For people considering getting involved in an open source community,
# they may want to know how long it will take to integrate into the community.
# (Note: this ignores time spent in forums/IRC/slack/jabber etc)
#
# Get a user out of the first-interactions.txt file
# Search the other files for that user
# Find the time difference between first interaction and first:
# - opened issue (exclude if first interaction was opening an issue)
# - response on another's issue (exclude if this was their first interaction)
# - got a PR merged (if first interaction was an opened PR, this is still fine)
# - reviewed a PR (exclude if first interaction)
# - merged a PR (FIXME: we don't currently look for this as a first interaction)
#
# Hint: read file into memory with .read() and then use re.findall(pattern, file contents)
# A box plot would be good to show median, quartiles, max/min, and perhaps the underlying data?
# https://plot.ly/python/box-plots/
def graphRampTime(repoPath):
    with open(os.path.join(repoPath, 'responders.txt')) as respondersFile:
        responders = respondersFile.read()
    # No clue why readline is returning single characters, so let's do it this way:
    with open(os.path.join(repoPath, 'first-interactions.txt')) as newcomersFile:
        newcomers = newcomersFile.read().split('\n')

    deltaResponse = []
    noResponse = []
    firstResponse = []
    for line in newcomers:
        # FIXME: for some reason there's some blank lines in responders.txt?
        if len(line.split('\t')) < 4:
            continue
        user = line.split('\t')[0]
        startDate = datetime.strptime(line.split('\t')[3], "%Y-%m-%dT%H:%M:%SZ")
        # Find the time it took for a user to start
        # commenting on an issue someone else opened.
        pattern = re.compile(r'^responder\t(.*)\t%s\t.*\n' % user, re.MULTILINE)
        responseDates = re.findall(pattern, responders)
        responseDates.sort()
        if responseDates:
            nextDate = datetime.strptime(responseDates[0], "%Y-%m-%dT%H:%M:%SZ")
            delta = nextDate - startDate
            deltaResponse.append(delta.days)
        else:
            noResponse.append(user)

    # Now graph it!
    data = [Histogram(x=deltaResponse)]
    fig = Figure(data=data)
    offline.plot(fig, filename=os.path.join(repoPath, 'responders-rampup.html'), auto_open=False)
    # We can do subplots to show how many users have and haven't participated in that role
    # We can do subplots to show how many users have and haven't participated in that role
    print('Mean:', statistics.mean(deltaResponse), 'days')
    print('Median:', statistics.median(deltaResponse), 'days')
    print('Standard deviation:', statistics.pstdev(deltaResponse))

# Make a better contribution graph for a project over time
def main():
    parser = argparse.ArgumentParser(description='Gather statistics from scraped github information.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    args = parser.parse_args()
    repoPath = os.path.join(args.owner, args.repository)
    graphRampTime(repoPath)

if __name__ == "__main__":
    main()

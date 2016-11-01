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

def sortContributors(data):
    """Returns a dictionary with username as the key to return a list of contributions,
    sorted in order by date."""
    dates = {}
    for line in data.split('\n'):
        lineSplit = line.split('\t')
        if len(lineSplit) < 4:
            continue
        user = lineSplit[2]
        startDate = datetime.strptime(lineSplit[1], "%Y-%m-%dT%H:%M:%SZ")
        if user in dates:
            dates[user].append(startDate)
        else:
            dates[user] = [startDate]
    for user, date in dates.items():
        dates[user].sort()
    return dates

def getRampTime(newcomers, contributionDates, contributionType):
    deltaContribution = []
    noContribution = []

    for line in newcomers:
        lineSplit = line.split('\t')
        # FIXME: for some reason there's some blank lines in our data
        if len(lineSplit) < 4:
            continue
        user = lineSplit[0]
        startDate = datetime.strptime(lineSplit[3], "%Y-%m-%dT%H:%M:%SZ")
        # Find the time it took for a user to start contributing
        # in a particular way from the date of their first interaction
        # with the project. Note their first interaction could be this
        # contribution type.
        if not user in contributionDates:
            noContribution.append(user)
            continue
        nextDate = contributionDates[user][0]
        delta = nextDate - startDate
        if delta.days < 0:
            print('Negative delta for user', user, 'for', contributionType, 'on', nextDate)
            print('first contribution was on', startDate, 'file', os.path.join(lineSplit[1], lineSplit[2]))
            continue
        deltaContribution.append(delta.days)

    return deltaContribution, noContribution

def graphRampTime(deltas, nocontribs, graphtitle, xtitle, filename):
    data = [Histogram(x=deltas)]
    layout = Layout(
        title=graphtitle,
        yaxis=dict(title='Number of contributors'),
        xaxis=dict(title= xtitle +
                   '<br>Mean: ' + '{:.2f}'.format(statistics.mean(deltas)) + ' days, ' +
                   'Median: ' + '{:.2f}'.format(statistics.median(deltas)) + ' days' +
                   '<br>Number of contributors who did this: ' +
                   '{:,g}'.format(len(deltas)) +
                   '<br>Percentage of contributors who did this: ' +
                   '{:.2f}'.format(len(deltas)/(len(deltas)+len(nocontribs))*100) + '%')
    )
    fig = Figure(data=data, layout=layout)
    offline.plot(fig, filename=filename, auto_open=False)

def graphFrequency(data, graphtitle, xtitle, filename):
    data = [Scatter(x=[coord[0] for coord in data],
                    y=[coord[1] for coord in data],
                    mode = 'markers',
                   text=[coord[2] for coord in data])]
    layout = Layout(
        title=graphtitle,
        yaxis=dict(title='Number of contributions'),
        xaxis=dict(title= xtitle),
    )
    fig = Figure(data=data, layout=layout)
    offline.plot(fig, filename=filename, auto_open=False)

# Given a dictionary that contains lists of contribution dates,
# find number of weeks involved as X role and
# number of contributions in that role
def getFrequency(contributorDates):
    data = []
    nodata = 0
    for user, d in contributorDates.items():
        if len(d) < 2:
            nodata = nodata + 1
        else:
            length = (d[-1] - d[0]).days / 7.
            #if length != 0:
            #contribsPerWeek = len(d) / length
            contribs = len(d)
            data.append((length, contribs, user))
    return data, nodata

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
def createGraphs(repoPath):
    # No clue why readline is returning single characters, so let's do it this way:
    with open(os.path.join(repoPath, 'first-interactions.txt')) as newcomersFile:
        newcomers = newcomersFile.read().split('\n')

    info = [['responder', 'Bug triaging', 'a contributor comments on an issue opened by another person'],
            ['merger', 'Merger', 'a contributor merges a pull request'],
            ['reporter', 'Issue reporter', 'a contributor opens an issue'],
            ['reviewer', 'Pull request reviewer', 'a contributor comments on a pull request opened by another person'],
           ]

    for i in info:
        with open(os.path.join(repoPath, i[0] + 's.txt')) as f:
            contributors = f.read()
        i.append(sortContributors(contributors))
        deltaResponse, noResponse = getRampTime(newcomers, i[3], i[0])
        graphRampTime(deltaResponse, noResponse,
                      '%s ramp up time for newcomers to<br>' % i[1] + repoPath,
                      '<br>Number of days before %s' % i[2],
                      os.path.join(repoPath, i[0] + 's-rampup.html'))
        freq, nodata = getFrequency(i[3])
        graphFrequency(freq,
                      '%s frequency for contributors to<br>' % i[1] + repoPath,
                      '<br>Length of time (weeks) spent in that role',
                      os.path.join(repoPath, i[0] + 's-frequency.html'))


# Make a better contribution graph for a project over time
def main():
    parser = argparse.ArgumentParser(description='Gather statistics from scraped github information.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    args = parser.parse_args()
    repoPath = os.path.join(args.owner, args.repository)
    createGraphs(repoPath)

if __name__ == "__main__":
    main()

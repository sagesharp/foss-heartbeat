#!/usr/bin/env python3
#
# Copyright 2016 Sarah Sharp <sharp@otter.technology>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
import numpy
from datetime import datetime, timedelta
from plotly.offline import download_plotlyjs, init_notebook_mode, iplot, offline
from plotly.graph_objs import *
from ghcategorize import jsonIsPullRequest, jsonIsPullRequestComment
from ghreport import overwritehtml
from ghsentimentstats import graphSentiment
from ghsentimentstats import htmlSentimentStats

def issueDir(longerDir):
    return re.sub(r'(.*?issue-[0-9]+).*', '\g<1>', longerDir)

def prOpenTimes(owner, repo):
    repoPath = os.path.join(owner, repo)
    with open(os.path.join(repoPath, 'contributors.txt')) as contributorsFile:
        contributors = contributorsFile.read().split('\n')
    with open(os.path.join(repoPath, 'mergers.txt')) as mergersFile:
        mergers = mergersFile.read().split('\n')

    # Get rid of any misformated lines
    mergers = [m for m in mergers if len(m.split('\t')) > 3]
    # The fourth item on the line is the file name
    # For mergers, it may be a comment-*.json
    # For contributors, it may be a pr_*.json
    # Use the issue-* directory as the key
    d = {issueDir(c.split('\t')[3]): [c.split('\t')[1]] for c in contributors if len(c.split('\t')) > 3}

    # Note: we could have two mergers because someone asked bors to merge
    # something for them.  This will add a bit of noise to the data, but we
    # expect bors to be fast, so the time difference shouldn't matter.
    # If we've already recorded a merger, skip the insertion.
    for m in mergers:
        if len(m.split('\t')) < 3:
            continue
        key = issueDir(m.split('\t')[3])
        if not key in d.keys():
            print("Someone marked in mergers.txt as merger for unmerged issue", key)
            continue
        if len(d[key]) == 2:
            continue
        d[key].append(m.split('\t')[1])

    coords = [(datetime.strptime(value[0], "%Y-%m-%dT%H:%M:%SZ"),
               datetime.strptime(value[1], "%Y-%m-%dT%H:%M:%SZ"))
               for k, value in d.items()]
    coords.sort()
    return coords

def graphMergeDelay(coords):
    # Calculate, for each month, the average "age" of pull requests
    # (the average amount of time a pull request is open before being merged).
    # Discard all PRs opened after the end of the month
    # discard all PRs closed before the beginning of the month
    # in order to only look at PRs closed this month.
    #
    #       Jan                                 Feb
    # |---------1--------|
    #           |-------2---------|
    #               |---2---|
    #                           |-----------3------------|
    #
    # 1. If a pull request was opened before this month and closed this month,
    #    count the length of time from when it was opened to when it was closed.
    # 2. If a pull request was opened and closed in this month,
    #    count the length of time from when it was opened to when it was closed.
    # 3. If a pull request was opened this month but was not closed this month,
    #    count the length of time from when it was opened to the end of this month.
    #
    # (So essentially, from when it was open to when it was closed or EOM,
    # whichever is sooner)

    beg = coords[0][0]
    end = coords[-1][0]
    means = []
    bom = datetime(beg.year, beg.month, 1)
    while True:
        if bom.month+1 <= 12:
            eom = datetime(bom.year, bom.month+1, bom.day)
        else:
            eom = datetime(bom.year+1, 1, bom.day)
        openpr = [(x, min(y, eom)) for (x, y) in coords if x < eom and y > bom]
        if not openpr:
            means.append((eom, 0))
            bom = eom
            continue
        lengths = [(y - x).total_seconds() / (60*60*24.) for (x, y) in openpr]
        means.append((eom, numpy.average(lengths)))
        bom = eom
        if eom > end:
            break

    # Scatter chart - x is creation date, y is number of days open
    data = [
        Scatter(x=[x for (x, y) in coords],
                y=[(y - x).total_seconds() / (60*60*24.)
                   for (x, y) in coords],
                mode='markers',
                name='Pull requests<BR>by creation date'
               ),
        Scatter(x=[x for (x, y) in means],
                y=[y for (x, y) in means],
                name='Average time open'
               ),
    ]
    layout = Layout(
        title='Number of days a pull request is open',
        yaxis=dict(title='Number of days open'),
        xaxis=dict(title='Pull request creation date'),
    )
    fig = Figure(data=data, layout=layout)
    return offline.plot(fig, show_link=False, include_plotlyjs=False, output_type='div')

# Create a bar chart showing the ways different newcomers get involved
def graphNewcomers(repoPath, newcomers):
    # Sometimes we get bad data?
    newcomers = [x for x in newcomers if len(x.split('\t')) >= 4]

    issue = [x for x in newcomers if x.split('\t')[2].startswith('issue')]
    comment = [x for x in newcomers if x.split('\t')[2].startswith('comment')]
    pull = [x for x in newcomers if jsonIsPullRequest(x.split('\t')[2])]
    commentPR = [x for x in newcomers if jsonIsPullRequestComment(x.split('\t')[2])]
    # For each line, pull out the filename (third item)
    data = [
        Bar(x=['Opened an issue', 'Commented on an issue<BR>opened by someone else', 'Opened a pull request', 'Commented on a pull request<BR>opened by someone else'],
            y= [len(issue), len(comment), len(pull), len(commentPR)],
           )]
    layout = Layout(
        title='First contribution types for<BR>' + repoPath,
    )
    fig = Figure(data=data, layout=layout)
    return offline.plot(fig, show_link=False, include_plotlyjs=False, output_type='div')

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
    return offline.plot(fig, show_link=False, include_plotlyjs=False, output_type='div')

# FIXME Maybe look for the word 'bot' in the user description?
def getBots():
    return ['bors', 'bors-servo', 'googlebot', 'highfive', 'k8s-ci-robot', 'k8s-merge-robot', 'k8s-reviewable', 'rust-highfive', 'rfcbot']

def graphFrequency(data, graphtitle, xtitle, filename):
    botNames = getBots()
    data = sorted(data, key=lambda tup: tup[2], reverse=True)
    # Filter out any bots
    bots = [x for x in data if x[3] in botNames]
    nobots = [x for x in data if not (x[3] in botNames)]
    # Filter out contributors who have been inactive for a year
    recent = nobots[0][4]
    for x in nobots:
        if x[4] > recent:
            recent = x[4]
    recent = datetime(recent.year - 1, recent.month, recent.day, recent.hour, recent.minute, recent.second, recent.microsecond)
    inactive = [x for x in nobots if x[4] < recent]
    active = [x for x in nobots if x[4] >= recent]

    # Divide the remaining list into roughly fourths
    # to get 25th, 50th, 75th percentiles
    # Up to 3 extra people may end up in the last quartile
    # FIXME: I'm sure there's a more Pythonic way to do this
    quartiles = []
    chunks = int(len(active)/4)
    for i in range(0, 4):
        if i != 3:
            quartiles.append(active[(chunks*i):(chunks*(i+1))])
        else:
            quartiles.append(active[(chunks*i):len(active)+1])
    data = []
    labels = [
        ('rgba(213, 94, 0, .8)', 'Top 25% of active contributors'),
        ('rgba(230, 159, 0, .8)', 'Above average active contributors'),
        ('rgba(86, 180, 233, .8)', 'Somewhat active contributors'),
        ('rgba(0, 114, 178, .8)', 'Least active contributors'),
    ]
    for i in range(4):
        data.append(
            Scatter(x=[coord[0] for coord in quartiles[i]],
                    y=[coord[1] for coord in quartiles[i]],
                    name=labels[i][1],
                    mode = 'markers',
                    text=[coord[3] for coord in quartiles[i]],
                    marker=dict(color=labels[i][0])
                   )
        )
    if inactive:
        data.append(Scatter(x=[coord[0] for coord in inactive],
                        y=[coord[1] for coord in inactive],
                        name='Inactive for more than 1 year',
                        mode = 'markers',
                        text=[coord[3] for coord in inactive],
                        marker=dict(color='rgba(0, 0, 0, .8)')
                           )
                   )
    if bots:
        data.append(Scatter(x=[coord[0] for coord in bots],
                        y=[coord[1] for coord in bots],
                        name='Bots',
                        mode = 'markers',
                        text=[coord[3] for coord in bots],
                        marker=dict(color='rgba(240, 228, 66, .8)')
                           )
                   )
    layout = Layout(
        title=graphtitle,
        yaxis=dict(title='Number of contributions'),
        xaxis=dict(title= xtitle),
    )
    fig = Figure(data=data, layout=layout)
    return offline.plot(fig, show_link=False, include_plotlyjs=False, output_type='div')

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
            if length != 0:
                contribsPerWeek = len(d) / length
            else:
                contribsPerWeek = 0
            contribs = len(d)
            data.append([length, contribs, contribsPerWeek, user, d[-1]])
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
def createGraphs(owner, repo, htmldir):
    repoPath = os.path.join(owner, repo)
    # No clue why readline is returning single characters, so let's do it this way:
    with open(os.path.join(repoPath, 'first-interactions.txt')) as newcomersFile:
        newcomers = newcomersFile.read().split('\n')
    html = {'newcomers-ramp': graphNewcomers(repoPath, newcomers)}

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
        html[i[0] + '-ramp'] = graphRampTime(deltaResponse, noResponse,
                      '%s ramp up time for newcomers to<br>' % i[1] + repoPath,
                      '<br>Number of days before %s' % i[2],
                      os.path.join(repoPath, i[0] + 's-rampup.html'))
        freq, nodata = getFrequency(i[3])
        html[i[0] + '-freq'] = graphFrequency(freq,
                      '%s frequency for contributors to<br>' % i[1] + repoPath,
                      '<br>Length of time (weeks) spent in that role',
                      os.path.join(repoPath, i[0] + 's-frequency.html'))
    coords = prOpenTimes(owner, repo)
    html['mergetime'] = graphMergeDelay(coords)
    if 'all-comments-sentiment.txt' in os.listdir(repoPath):
        html['sentimentwarning'] = '<p><b>**WARNING** The sentiment model is not very good at classifying sentences yet. Take these graphs with a giant lump of salt.</b></p>'
        html['sentimentgraph'] = graphSentiment(repoPath, False)
        html['sentimentstats'] = htmlSentimentStats(repoPath)
    else:
        html['sentimentwarning'] = ''
        html['sentimentgraph'] = '<p>More data coming soon! Click another tab.</p>'
        html['sentimentstats'] = ''

    # Use bootstrap to generate mobile-friendly webpages
    overwritehtml(htmldir, owner, repo, html)

# Make a better contribution graph for a project over time
def main():
    parser = argparse.ArgumentParser(description='Gather statistics from scraped github information.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    parser.add_argument('htmldir', help='directory where report templates and project reports are stored')
    args = parser.parse_args()
    createGraphs(args.owner, args.repository, args.htmldir)

if __name__ == "__main__":
    main()

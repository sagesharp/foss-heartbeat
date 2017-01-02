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

import argparse
from collections import defaultdict
from datetime import datetime
import itertools
import json
import os
import re
import statistics
from plotly.offline import download_plotlyjs, init_notebook_mode, iplot, offline
from plotly.graph_objs import *
from ghcategorize import getUserDate

def labelToNumber(label):
    if re.match('^  Very positive', label):
        return 4
    if re.match('^  Positive', label):
        return 3
    if re.match('^  Neutral', label):
        return 2
    if re.match('^  Negative', label):
        return 1
    if re.match('^  Very negative', label):
        return 0
    return None

def scrubSentimentizedComment(sentiment):
    # Split by newlines
    sentiment = sentiment.splitlines()
    # Strip out the first four lines, since those are always
    # Comment file string (with repo name stripped out)
    #   Sentiment from issue name (usually Negative)
    # json .
    #   Sentiment from that (also usually Negative)
    sentiment = sentiment[4:]
    slist = []
    siter = iter(sentiment)
    try:
        while True:
            comment = ''
            line = next(siter)
            while not re.match('^  Very positive$|^  Positive$|^  Neutral$|^  Negative$|^  Very negative$', line):
                comment = comment + line
                line = next(siter)
            if not re.match('^.$', comment):
                slist.append((labelToNumber(line), comment))
    except StopIteration:
        pass
    return slist

def getSentimentCount(commentList, sentimentValue):
    filtered = [comment for (value, comment) in commentList if value == sentimentValue]
    return len(filtered)

def printWeighted(slist, name):
    weightedPositiveSentiment = {key: (item[3]*(1) + item[4]*(2))/sum(item) for key, item in slist.items() if sum(item) > 0}
    weightedNegativeSentiment = {key: (item[0]*(-2) + item[1]*-1)/sum(item) for key, item in slist.items() if sum(item) > 0}
    weightedNeutralSentiment = {key: (item[2])/sum(item) for key, item in slist.items() if sum(item) > 0}
    print()
    print("Average weighted", name, "sentiment: %+0.2f" % statistics.mean(weightedPositiveSentiment.values()), "|",
          "%0.2f" % statistics.mean(weightedNeutralSentiment.values()), "|",
          "%+0.2f" % statistics.mean(weightedNegativeSentiment.values()),
         )

def createSentimentDict(repoPath):
    with open(os.path.join(repoPath, 'all-comments-sentiment.txt')) as sfile:
        c = sfile.read().split('\n#' + repoPath + os.sep)

    # The first comment isn't going to have a newline, so make it conform
    c[0] = c[0].split('#' + repoPath + os.sep)[1]
    d = {os.path.join(repoPath, line.split('\n')[0] + 'json'): scrubSentimentizedComment(line) for line in c}
    return d

def createSentimentCounts(sentimentDict):
    # Get 5 count of sentiment per comment
    commentSentiment = {key: (getSentimentCount(value, 0),
                         getSentimentCount(value, 1),
                         getSentimentCount(value, 2),
                         getSentimentCount(value, 3),
                         getSentimentCount(value, 4),
                        )
                        for key, value in sentimentDict.items()}
    return commentSentiment

def createIssueSentiment(commentSentiment):
    issueSentiment = defaultdict(list)
    for key, value in commentSentiment.items():
        issueSentiment[key.split(os.sep)[2]].append(value)
    combinedIssueSentiment = {key:
                              (sum([item[0] for item in sentimentList]),
                              sum([item[1] for item in sentimentList]),
                              sum([item[2] for item in sentimentList]),
                              sum([item[3] for item in sentimentList]),
                              sum([item[4] for item in sentimentList]),)
                              for key, sentimentList in issueSentiment.items()
                             }
    return combinedIssueSentiment

def createJsonDict(repoPath, issueKeys, debug):
    # issueDict has the issue numbers (e.g. issue-23529) as keys
    # Create a dictionary for each json comment file
    # key (path): (date, user)
    # First grab lines from the categorized project csv files.
    # Ignore any lines with the username bors as merger,
    # since both bors and the user who sent a command to bors
    # will be marked as a merger for the same json PR comment file.
    jsonDict = defaultdict(list)
    for f in ['contributors.txt', 'mergers.txt', 'reporters.txt', 'responders.txt', 'reviewers.txt', 'submitters.txt']:
        with open(os.path.join(repoPath, f)) as tabsFile:
            lines = tabsFile.read().splitlines()
        fileTuples = [l.split('\t')[1:] for l in lines if len(l.split('\t')) > 3 and (f != 'mergers.txt' and l.split('\t')[2] != 'bors')]
        for f in fileTuples:
            date = f[0]
            username = f[1]
            path = f[2]
            jsonDict[path] = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"), username)
    dictSize = len(jsonDict)
    if debug:
        print('Added', len(jsonDict), 'categorized json files')

    # It's possible that an issue or PR's first json file has no comments,
    # so manually add the date and username of the person that opened this issue.
    for k in [os.path.join(repoPath, key, key + '.json') for key in issueKeys if os.path.join(repoPath, key, key + '.json') not in jsonDict.keys()]:
        with open(k) as issueFile:
            issueJson = json.load(issueFile)
        user, date = getUserDate(issueJson)
        jsonDict[k] = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"), user)
    if debug:
        print('Added', len(jsonDict) - dictSize, 'uncategorized json files')
    return jsonDict

def graphSentiment(repoPath, debug):
    sentimentDict = createSentimentDict(repoPath)
    commentSentiment = createSentimentCounts(sentimentDict)
    combinedIssueSentiment = createIssueSentiment(commentSentiment)

    if debug:
        print('Have', len(commentSentiment), 'sentiment json files')
    jsonDict = createJsonDict(repoPath, combinedIssueSentiment.keys(), True)
    
    # List: [date, issue path (for now), (combinedIssueSentiment 5 tuple)]
    coords = []
    for key, value in combinedIssueSentiment.items():
        try:
            path = os.path.join(repoPath, key, key + '.json')
            with open(path) as issueFile:
                issueJson = json.load(issueFile)
            url = issueJson['html_url']
            coords.append((jsonDict[path][0], key, value, url))
        except:
            key2 = os.path.join(repoPath, key, key + '.json')
            if debug:
                print(key, 'IS in combinedIssueSentiment dict')
                print(key2, 'NOT in jsonDict')
                if key2 not in sentimentDict.keys():
                    print(key2, 'NOT in sentimentDict')
                else:
                    print(key2, 'IS in sentimentDict')
                if key2 not in commentSentiment.keys():
                    print(key2, 'NOT in commentSentiment dict')
                else:
                    print(key2, 'IS in commentSentiment dict')
            #print(key, value, key.split(os.sep))
            pass
    if debug:
        print('coords len:', len(coords), 'number issues:', len(combinedIssueSentiment))

    coords = sorted(coords, key=lambda tup: tup[1])
    # Multiplier - what is the magnitude of positive comments you would have to receive vs negative comments
    # to have this issue "feel" positive?
    feelsMultipler = 2
    posCoords = [(date, issue, sentiment, url) for (date, issue, sentiment, url) in coords
                 if (sentiment[4]*2 + sentiment[3]) > feelsMultipler*(sentiment[0]*2 + sentiment[1])
                ]
    negCoords = [(date, issue, sentiment, url) for (date, issue, sentiment, url) in coords
                 if (sentiment[0]*2 + sentiment[1]) > feelsMultipler*(sentiment[4]*2 + sentiment[3])
                ]
    # Issues can have a lot of neutral comments (debate on code) and still "feel" negative or mixed.
    # If more than 20% of the comments are positive or neutral, it's a mixed thread.
    mixedPercent = .20
    neutralCoords = [(date, issue, sentiment, url) for (date, issue, sentiment, url) in coords
                     if (sentiment[2] > 0)
                     and (mixedPercent > ((sentiment[0]*2 + sentiment[1] + sentiment[3] + sentiment[4]*2) / (sentiment[2])))
                     and ((date, issue, sentiment, url) not in posCoords)
                     and ((date, issue, sentiment, url) not in negCoords)
                    ]
    mixedCoords = [(date, issue, sentiment, url) for (date, issue, sentiment, url) in coords
                   if ((date, issue, sentiment, url) not in neutralCoords)
                   and ((date, issue, sentiment, url) not in posCoords)
                   and ((date, issue, sentiment, url) not in negCoords)
                  ]
    sentCoords = [
        ('Neutral', 'rgba(0, 0, 0, .8)', neutralCoords),
        ('Positive', 'rgba(21, 209, 219, .8)', posCoords),
        ('Negative', 'rgba(250, 120, 80, .8)', negCoords),
        ('Mixed', 'rgba(130, 20, 160, .8)', mixedCoords),
    ]

    data = []
    for s in sentCoords:
        data.append(Scatter(x=[date for (date, issue, sentiment, url) in s[2]],
                            y=[sentiment[2] for (date, issue, sentiment, url) in s[2]],
                            error_y=dict(
                                type='data',
                                symmetric=False,
                                array=[sentiment[3]+sentiment[4]*2 for (date, issue, sentiment, url) in s[2]],
                                arrayminus=[sentiment[1]+sentiment[0]*2 for (date, issue, sentiment, url) in s[2]],
                                color=s[1],
                            ),
                            mode = 'markers',
                            text = [url for (date, issue, sentiment, url) in s[2]],
                            name=s[0] + ' community sentiment',
                            marker=dict(color=s[1]),
               ))
    layout = Layout(
        title='Community sentiment',
        yaxis=dict(title='Number of + positive | neutral | - negative comments'),
        xaxis=dict(title='Issue or PR creation date'),
    )
    fig = Figure(data=data, layout=layout)
    return offline.plot(fig, show_link=False, auto_open=False, include_plotlyjs=False, output_type='div')

def htmlSentimentStats(repoPath):
    sentimentDict = createSentimentDict(repoPath)
    commentSentiment = createSentimentCounts(sentimentDict)
    combinedIssueSentiment = createIssueSentiment(commentSentiment)

    htmlString = ''
    htmlString = htmlString + '<p>' + "On average, an issue or pull request in " + repoPath + " contains:" + '\n'
    htmlString = htmlString + '<ul>\n'
    htmlString = htmlString + '<li>'+ "%0.2f very positive sentences" % statistics.mean([item[4] for item in combinedIssueSentiment.values()]) + '</li>\n'
    htmlString = htmlString + '<li>'+ "%0.2f positive sentences" % statistics.mean([item[3] for item in combinedIssueSentiment.values()]) + '</li>\n'
    htmlString = htmlString + '<li>'+ "%0.2f neutral sentences" % statistics.mean([item[2] for item in combinedIssueSentiment.values()]) + '</li>\n'
    htmlString = htmlString + '<li>'+ "%0.2f negative sentences" % statistics.mean([item[1] for item in combinedIssueSentiment.values()]) + '</li>\n'
    htmlString = htmlString + '<li>'+ "%0.2f very negative sentences" % statistics.mean([item[0] for item in combinedIssueSentiment.values()]) + '</li>\n'
    htmlString = htmlString + '</ul>'+ '</p>\n'

    htmlString = htmlString + '<p>' + "Chances of encountering a particular sentiment while filing an issue or pull request" + ':\n'
    htmlString = htmlString + '<ul>\n'
    htmlString = htmlString + '<li>'+ "Very positive: %0.2f%%" % (100*statistics.mean([bool(item[4]) for item in combinedIssueSentiment.values()])) + '</li>\n'
    htmlString = htmlString + '<li>'+ "Positive: %0.2f%%" % (100*statistics.mean([bool(item[3]) for item in combinedIssueSentiment.values()])) + '</li>\n'
    htmlString = htmlString + '<li>'+ "Neutral: %0.2f%%" % (100*statistics.mean([bool(item[2]) for item in combinedIssueSentiment.values()])) + '</li>\n'
    htmlString = htmlString + '<li>'+ "Negative: %0.2f%%" % (100*statistics.mean([bool(item[1]) for item in combinedIssueSentiment.values()])) + '</li>\n'
    htmlString = htmlString + '<li>'+ "Very negative: %0.2f%%" % (100*statistics.mean([bool(item[0]) for item in combinedIssueSentiment.values()])) + '</li>\n'
    htmlString = htmlString + '</ul>'+ '</p>\n'

    # Flamewars: Generate a list of threads with high negative sentiment and larger than median number of comments
    # Rubust statistics (see wikipedia) - quartiles?
    return htmlString

def main():
    parser = argparse.ArgumentParser(description='Output statistics comparing sentiment of multiple communities')
    parser.add_argument('repoPath', help='github repository name')
    args = parser.parse_args()

    repoPath = args.repoPath
    html = graphSentiment(repoPath, True)
    print(html)
    print(htmlSentimentStats(repoPath))

if __name__ == "__main__":
    main()

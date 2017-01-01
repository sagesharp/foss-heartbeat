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
import os
import re
import statistics

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

def main():
    parser = argparse.ArgumentParser(description='Output statistics comparing sentiment of multiple communities')
    parser.add_argument('repoPath', help='github repository name')
    args = parser.parse_args()

    repoPath = args.repoPath
    with open(os.path.join(repoPath, 'all-comments-sentiment.txt')) as sfile:
        c = sfile.read().split('\n#' + repoPath + os.sep)

    # The first comment isn't going to have a newline, so make it conform
    c[0] = c[0].split('#' + repoPath + os.sep)[1]
    d = {os.path.join(repoPath, line.split('\n')[0] + 'json'): scrubSentimentizedComment(line) for line in c}

    # Get 5 count of sentiment per comment
    commentSentiment = {key: (getSentimentCount(value, 0),
                         getSentimentCount(value, 1),
                         getSentimentCount(value, 2),
                         getSentimentCount(value, 3),
                         getSentimentCount(value, 4),
                        )
                        for key, value in d.items()}
    
    # Average, median, and std dev number of comments per issue
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
    print()
    print("Average number of sentences of a particular sentiment per issue in", repoPath,)
    print("Very positive: %0.2f |" % statistics.mean([item[4] for item in combinedIssueSentiment.values()]),
          "Positive: %0.2f |" % statistics.mean([item[3] for item in combinedIssueSentiment.values()]),
          "Neutral: %0.2f |" % statistics.mean([item[2] for item in combinedIssueSentiment.values()]),
          "Negative: %0.2f |" % statistics.mean([item[1] for item in combinedIssueSentiment.values()]),
          "Very negative: %0.2f |" % statistics.mean([item[0] for item in combinedIssueSentiment.values()]),
         )
    print()
    print("Chances of getting a particular comment sentiment in an issue", repoPath,)
    print("Very positive: %0.2f%% |" % (100*statistics.mean([bool(item[4]) for item in combinedIssueSentiment.values()])),
          "Positive: %0.2f%% |" % (100*statistics.mean([bool(item[3]) for item in combinedIssueSentiment.values()])),
          "Neutral: %0.2f%% |" % (100*statistics.mean([bool(item[2]) for item in combinedIssueSentiment.values()])),
          "Negative: %0.2f%% |" % (100*statistics.mean([bool(item[1]) for item in combinedIssueSentiment.values()])),
          "Very negative: %0.2f%% |" % (100*statistics.mean([bool(item[0]) for item in combinedIssueSentiment.values()])),
         )
    print()

    # Flamewars: Generate a list of threads with high negative sentiment and larger than median number of comments
    # Rubust statistics (see wikipedia) - quartiles?

if __name__ == "__main__":
    main()

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
# Does a particular word from another developer have an impact on whether someone contributes again?
#
# Resources:
#  - a project's all-comments.txt file, produced with the following command:
#    python ../src/ghsentiment.py owner/repo/ owner/repo/all-comments.txt --recurse
#  - usernames from owner/repo/first-interactions.txt, produced with the following command:
#    python ghcategorize.py repo owner
#  - info from owner/repo/submitters.txt
#
# Plan:
#  - sort PR submitters (or issue submitters, later) into dict - username, list of (PR directory, created by date)
#  - sort all-comments.txt into dict - directory, list of (json file, username, date)
#  - find out if any of the comments from the users who didn't submit the PR contain the word thanks or thank
#  - two populations - those who are thanked, those who aren't - did they submit again is success criteria
#  - plug total and number of successes for each population into http://www.evanmiller.org/ab-testing/chi-squared.html

from ghstats import issueDir
from operator import itemgetter
import os
import re
import json
import argparse
from datetime import datetime

def createContributionDict(repoPath, fileList):
    contribDict = {}
    lines = []
    for x in fileList:
        with open(os.path.join(repoPath, x)) as f:
            lines = lines + f.read().split('\n')

    # key (username): date, issue directory
    contribs = [(x.split('\t')[2],
                 datetime.strptime(x.split('\t')[1], "%Y-%m-%dT%H:%M:%SZ"),
                 issueDir(x.split('\t')[3]))
                for x in lines if len(x.split('\t')) > 3]
    contribs = sorted(contribs, key=itemgetter(1))
    for c in contribs:
        contribDict.setdefault( c[0], [] ).append((c[1], c[2]))
    return contribDict

def createReviewerDict(repoPath, fileList):
    contribDict = {}
    lines = []
    for x in fileList:
        with open(os.path.join(repoPath, x)) as f:
            lines = lines + f.read().split('\n')

    # key (json file path): date, user
    contribs = [(x.split('\t')[3],
                 datetime.strptime(x.split('\t')[1], "%Y-%m-%dT%H:%M:%SZ"),
                 x.split('\t')[2])
                for x in lines if len(x.split('\t')) > 3]
    for c in contribs:
        contribDict[c[0]] = [(c[1], c[2])]
    return contribDict

def createCommentDict(repoPath):
    with open(os.path.join(repoPath, 'all-comments.txt')) as f:
        # We want the trailing json file path
        c = f.read().split('\n#' + repoPath + os.sep)
    # The first comment isn't going to have a newline, so make it conform
    c[0] = c[0].split('#' + repoPath + os.sep)[1]
    d = {os.path.join(repoPath, line.split('\n')[0].strip(' .')): line for line in c}
    return d

def main():
    parser = argparse.ArgumentParser(description='Compares whether people come back after experiencing a specific word from a community')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    parser.add_argument('regex', help='word or python regex to search for (MULTILINE is enabled)')
    parser.add_argument('--skip', help='if this python regex is matched, ignore this comment', type=str, default=None)
    parser.add_argument('--num', help='number of contributions that are considered a success', type=int, default=1)
    parser.add_argument('--reporters', help='intead of looking and PR submitters and reviewers, look at bug reporters and responders', type=bool, default=False)
    parser.add_argument('--printmissing', help="print issues where contributors didn't experience the word", type=bool, default=False)
    parser.add_argument('--skipopen', help="don't count any issues or pull requests that are still open", type=bool, default=False)
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)
    # Grab both merged and not merged pull requests

    # PR key (username): [(date, issue directory), ... ]
    if args.reporters:
        contribDict = createContributionDict(repoPath, ['reporters.txt'])
    else:
        contribDict = createContributionDict(repoPath, ['contributors.txt', 'submitters.txt'])
    # Reviews key (json file path): [(date, user)]
    if args.reporters:
        reviewDict = createReviewerDict(repoPath, ['responders.txt'])
    else:
        reviewDict = createReviewerDict(repoPath, ['reviewers.txt'])
    # Reviews key (json file path): multiline comment string
    commentDict = createCommentDict(repoPath)

    thanked = 0
    noThanked = 0
    thankedSuccess = 0
    noThankedSuccess = 0
    for key, value in contribDict.items():
        # Grab the user's first contribution to the project
        firstPR = value[0]
        issueDir = firstPR[1]
        tflag = False
        reviewComments = 0
        for c in [os.path.join(issueDir, x) for x in os.listdir(issueDir)]:
            # Ignore any files where the PR creator commented
            if c not in reviewDict.keys():
                continue
            if c not in commentDict.keys():
                print("WARN", c, "not in all-comments.txt")
                continue
            reviewComments = reviewComments + 1
            comment = commentDict[c]
            if args.skip and re.search(args.skip, comment, flags=re.MULTILINE):
                continue
            if re.search(args.regex, comment, flags=re.MULTILINE):
                tflag = True
        if tflag:
            thanked = thanked + 1
            if len(value) > args.num:
                thankedSuccess = thankedSuccess + 1
        else:
            if args.printmissing:
                for c in [os.path.join(issueDir, x) for x in os.listdir(issueDir)]:
                    if c not in reviewDict.keys() or c not in commentDict.keys():
                        continue
                    print(commentDict[c])
            # Skip any issues where no one but the submitter commented.
            # This could be because the submitter closed it.
            if not reviewComments:
                if args.printmissing:
                    print("Issue with no comments:", issueDir)
                continue
            # Skip any issues that have comments but are still open.
            if args.skipopen:
                for jsonFile in os.listdir(issueDir):
                    if jsonFile.startswith('issue-'):
                        with open(os.path.join(issueDir, jsonFile)) as issueFile:
                            issueJson = json.load(issueFile)
                if issueJson['state'] ==  'open':
                    if args.printmissing:
                        print("Issue still open:", issueDir)
                        continue
            noThanked = noThanked + 1
            if len(value) > args.num:
                noThankedSuccess = noThankedSuccess + 1
    print("Number of first time contributors exposed to word:", thanked)
    print("Number of first time contributors exposed to word that contributed again:", thankedSuccess)
    print("Number of first time contributors NOT exposed to word:", noThanked)
    print("Number of first time contributors NOT exposed to word that contributed again:", noThankedSuccess)

if __name__ == "__main__":
    main()

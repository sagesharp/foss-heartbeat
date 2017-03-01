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
# This program categorizes github interactions stored in the format:
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
#
# The program writes the following files:
#
#  - first-interactions.txt
#    username, issue ID, file name of the issue comment/review comment/pull request ID,
#    and date of first interaction with the project
#
#    This contains a contributor's first interaction with the project.
#    They could have opened an issue, commented on an issue,
#    opened a pull request, or commented on a pull request.
#
#  - reporters.txt
#    'reporter', date, username, path to issue json file
#
#    This file contains users who have opened an issue (not a pull request).
#    Depending on what issues are used for, these people could be bug reporters,
#    feature proposers, etc.
#
#  - responders.txt
#   'responder', date, username, path to issue comment json file
#
#    This file contains comments people added to issues that they didn't open.
#    Depending on what issues are used for, this people could be triaging a bug,
#    responding to a feature request or RFC, etc.
#
#  - submitters.txt
#    'submitter', date, username, path to pull request json file
#
#    This file contains people who have opened a pull request that was not merged.
#
#  - contributors.txt
#    'contributor', date, username, path to pull request json file
#
#    This file contains people who have opened a pull request that was merged.
#
#  - reviewers.txt
#   'reviewer', date, username, path to pull request or issue comment json file
#
#    This file contains people who comment on pull requests (either as an issue comment
#    or as a contribution review comment) on pull requests they didn't open.
#
#  - mergers.txt
#    'merger', date, username, path to issue comment json file that contains a
#    bot command or path to pull request json file that was merged
#
#    This file contains people who merge pull requests (which may be their own)
#    Note that this file may contain bots who are merging in code on command.
#    We attempt to find the user who issued the command and record them as a merger,
#    in addition to the bot doing the merging.
#
# - connectors.txt
#
#   FIXME: add this.
#   This file contains people who tag another person who comments on an issue or PR.
#   These people are crucial for getting the right people to review a problem,
#   especially issues opened by newcomers who don't know who to tag.

import os
import re
import json
import argparse
from datetime import datetime

# Github lesson 2:
#
# If a user is deleted, their comments remain, but their user info is removed.
# On the github website, their user info will be linked to:
# https://github.com/ghost
# That means we can't differentiate between multiple deleted users.
def getUserDate(json):
    if not json['user']:
        user = 'ghost'
    else:
        user = json['user']['login']
    date = json['created_at']
    return user, date

# Track issue reporters
# Make a note when someone opened an issue (not a PR)
def appendIssueReporters(issueDir, issueReporters):
    """If an issue is not a pull request, append issue reporter information to the issueReporters list.
    Return the username of the issue reporter, or None if this is a pull request."""
    # Grab the json from the issue File
    for jsonFile in os.listdir(issueDir):
        if jsonFile.startswith('issue-'):
            with open(os.path.join(issueDir, jsonFile)) as issueFile:
                issueJson = json.load(issueFile)
                break
    if 'pull_request' in issueJson:
        return None
    user, date = getUserDate(issueJson)
    issueReporters.append(('reporter', date, user, os.path.join(issueDir, jsonFile)))
    return user

# Track issue responders
# Make a note when someone responded on an issue (not a PR) that is not their own
def appendIssueResponders(issueDir, issueResponders, issueCreator):
    for jsonFile in os.listdir(issueDir):
        if not jsonFile.startswith('comment-'):
            continue
        with open(os.path.join(issueDir, jsonFile)) as commentFile:
            commentJson = json.load(commentFile)
        user, date = getUserDate(commentJson)
        if user == issueCreator:
            continue
        issueResponders.append(('responder', date, user, os.path.join(issueDir, jsonFile)))

# FIXME: ugh, we could avoid pattern matching if we renamed pr-comment to review-comment
def jsonIsPullRequest(filename):
    return re.match(r'pr-[0-9]+', filename)

def jsonIsPullRequestComment(filename):
    return re.match(r'pr-comment-[0-9]+', filename)

# Track contributors with a merged pull request,
# submitters who opened a pull request that wasn't merged,
# and the mergers (people who merged those pull requests).
#
# Make a note when someone opened a PR
#
# Look in the pr-.json files. If it was merged, merged = true
# If it was merged, the person is a contributor,
# if they didn't get their code merged, they are a submitter.
#
# Can look for merged_by to get the user who merged it
# Not sure what happens when a 'ghost' has merged in a file
def appendContributor(issueDir, contributors, mergers, submitters):
    """If an issue is a pull request, append issue reporter information to the issueReporters list.
    Return the username of the issue reporter, or None if this is a pull request."""
    # Grab the json from the pull request file
    prJson = None
    for jsonFile in os.listdir(issueDir):
        if jsonIsPullRequest(jsonFile):
            with open(os.path.join(issueDir, jsonFile)) as prFile:
                prJson = json.load(prFile)
                break
    if not prJson:
        return None

    user, date = getUserDate(prJson)
    merged_at = prJson['merged_at']
    merger = prJson['merged_by']
    if merged_at:
        contributors.append(('contributor', date, user, os.path.join(issueDir, jsonFile)))
        if not merger:
            mergers.append(('merger', merged_at, 'ghost', os.path.join(issueDir, jsonFile)))
        else:
            mergers.append(('merger', merged_at, merger['login'], os.path.join(issueDir, jsonFile)))
    else:
        submitters.append(('submitter', date, user, os.path.join(issueDir, jsonFile)))
    return user

def checkForBotCommand(json, commandList):
    """If this was a command sent to a bot, return
    the username of the person who issued the command
    and the date of the command."""
    if not 'body_text' in json:
        return None
    for command in commandList:
        # FIXME: bot may check for commands in the middle of a comment?
        if json['body_text'] is not None:
            if json['body_text'].startswith(command):
                user, date = getUserDate(json)
                return user, date
    return None, None

# Track pull request reviewers, who may make an issue comment, or a PR review comment.
# If someone tagged a bot in order for that bot to merge the code in, add them as a merger.
def appendReviewers(issueDir, contributor, reviewers, mergers):
    for jsonFile in os.listdir(issueDir):
        if not jsonFile.startswith('comment-') and not jsonFile.startswith('pr-comment-'):
            continue
        with open(os.path.join(issueDir, jsonFile)) as commentFile:
            commentJson = json.load(commentFile)
        user, date = getUserDate(commentJson)
        merger, mergeDate = checkForBotCommand(commentJson, ['@bors: r+'])
        # FIXME: it's possible that the command was issued to bors,
        # but it rejected the pull request because it didn't pass.
        # Need to also check the 'merged' flag in the pr-*.json file.
        if merger and mergeDate:
            mergers.append(('merger', mergeDate, merger, os.path.join(issueDir, jsonFile)))
        if user == contributor:
            continue
        reviewers.append(('reviewer', date, user, os.path.join(issueDir, jsonFile)))

def createStats(repoPath):
    issueReporters = []
    issueResponders = []
    submitters = []
    contributors = []
    reviewers = []
    mergers = []

    processed = 0
    for directory in os.listdir(repoPath):
        if not directory.startswith('issue-'):
            continue
        dirPath = os.path.join(repoPath, directory)
        issueCreator = appendIssueReporters(dirPath, issueReporters)
        if issueCreator:
            appendIssueResponders(dirPath, issueResponders, issueCreator)
        else:
            prCreator = appendContributor(dirPath, contributors, mergers, submitters)
            if prCreator:
                appendReviewers(dirPath, contributors, reviewers, mergers)
        processed += 1
        if (processed % 1000) == 0:
            print('Processed', processed, 'issues')
    statsList = [(issueReporters, 'reporters.txt'),
                 (issueResponders, 'responders.txt'),
                 (submitters, 'submitters.txt'),
                 (contributors, 'contributors.txt'),
                 (reviewers, 'reviewers.txt'),
                 (mergers, 'mergers.txt')]
    return statsList

def insertUser(users, dirPath, jsonFile):
    """Helps create a dictionary of the user's first interactions with a project.
    Given a json file describing an opened issue or PR, or a comment,
    Insert user into the dictionary, but only overwrite the dict entry
    if this interaction is older than the one stored."""

    with open(os.path.join(dirPath, jsonFile)) as issueFile:
        soup = json.load(issueFile)
        key, date = getUserDate(soup)
    if not key in users:
        users[key] = (dirPath, jsonFile, date)
    else:
        stored = datetime.strptime(users[key][2], "%Y-%m-%dT%H:%M:%SZ")
        new = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        if new < stored:
            users[key] = (dirPath, jsonFile, date)

def findUsers(repoPath):
    """Returns a dictionary of username keys, with values being issue ID,
    the file name of the issue comment/review comment/pull request ID,
    and date of first interaction with the project."""
    users = {}
    for directory in os.listdir(repoPath):
        if not directory.startswith('issue-'):
            continue
        dirPath = os.path.join(repoPath, directory)

        dirList = os.listdir(dirPath)
        prFile = None
        # First, look whether this is an issue or a PR.
        # If it's a PR, make sure to insert that into the list,
        # because when a PR is opened, an issue is opened
        # with the same timestamp, and it's racy
        # which order listdir will return the file names in.
        for jsonFile in dirList:
            if jsonIsPullRequest(jsonFile):
                insertUser(users, dirPath, jsonFile)
                prFile = jsonFile

        for jsonFile in dirList:
            if not prFile or (prFile and prFile != jsonFile):
                insertUser(users, dirPath, jsonFile)
    return users

def main():
    parser = argparse.ArgumentParser(description='Categorize interactions with scraped github data.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)

    users = findUsers(repoPath)
    with open(os.path.join(repoPath, 'first-interactions.txt'), 'w') as interactionsFile:
        for key, value in users.items():
            interactionsFile.write(key + '\t' + value[0] + '\t' + value[1] + '\t' +  value[2] + '\n')

    statsList = createStats(repoPath)
    for stats in statsList:
        with open(os.path.join(repoPath, stats[1]), 'w') as statsFile:
            print('Writing', stats[1])
            for line in stats[0]:
                for item in line:
                    statsFile.write(item + '\t')
                statsFile.write('\n')

if __name__ == "__main__":
    main()

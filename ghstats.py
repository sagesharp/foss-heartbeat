#!/usr/bin/env python3
#
# Copyright 2016 Sarah Sharp <sharp@otter.technology>
#
# This program creates statistics from github issue data files in the format:
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

import os
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
            if prFile and prFile != jsonFile:
                insertUser(users, dirPath, jsonFile)
    return users

def main():
    parser = argparse.ArgumentParser(description='Gather statistics from scraped github information.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)

    users = findUsers(repoPath)
    with open(os.path.join(repoPath, 'first-interactions.txt', 'w')) as interactionsFile:
        for key, value in users.items():
            interactionsFile.write(key + '\t' + value[0] + '\t' + value[1] + '\t' +  value[2])

if __name__ == "__main__":
    main()

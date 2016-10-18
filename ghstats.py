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


def findUsers(repoPath):
    """Returns a dictionary of username keys, with values being issue ID,
    the file name of the issue comment/review comment/pull request ID,
    and date of first interaction with the project."""
    users = {}
    for directory in os.listdir(repoPath):
        if not directory.startswith('issue-'):
            continue
        dirPath = os.path.join(repoPath, directory)

        for jsonFile in os.listdir(dirPath):
            with open(os.path.join(dirPath, jsonFile)) as issueFile:
                soup = json.load(issueFile)
                # Github lesson 2:
                #
                # If a user is deleted, their comments remain, but their user info is removed.
                # On the github website, their user info will be linked to:
                # https://github.com/ghost
                # That means we can't differentiate between multiple deleted users.
                if not soup['user']:
                    key = 'ghost'
                else:
                    key = soup['user']['login']
                date = soup['created_at']
            # Insert user in, but only if this interaction is older
            if not key in users:
                users[key] = (dirPath, jsonFile, date)
            else:
                stored = datetime.strptime(users[key][2], "%Y-%m-%dT%H:%M:%SZ")
                new = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                if new < stored:
                    users[key] = (dirPath, jsonFile, date)
    return users

def main():
    parser = argparse.ArgumentParser(description='Gather statistics from scraped github information.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)

    users = findUsers(repoPath)
    for key, value in users.items():
        print(key, '\t', value[0], '\t', value[1], '\t',  value[2])

if __name__ == "__main__":
    main()

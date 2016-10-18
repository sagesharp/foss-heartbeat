#!/usr/bin/env python3
#
# Copyright 2016 Sarah Sharp <sharp@otter.technology>
#
# This python script scrapes github issue information, including comments.
# The script dumps the json strings into files in a tree structure:
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
# Github API rate limiting
# ------------------------
#
# Github limits API requests to 5,000 requests per hour.
# This means it can take hours or even days to scrape the data.
#
# There are projects that archive the public Github events stream:
# http://githubarchive.org/ and http://ghtorrent.org/
#
# However, they only go back to 2011 or 2012, and I'm unsure whether they
# include the body text as markdown or html (which is important for removing
# code snippets from the text passed to the sentiment analysis library.
#
# How we fetch the data
# =====================
#
# If the main method is called, data is fetched in an iterative fashion,
# in order to cut down on API calls as much as possible:
#
# 1. Fetch the list of all issues (up to 100 issues at a time),
#    write issue-<id>.json
#
# 2. Iterate over the issues json files, finding issues with comments.
#    For each issue with comments, fetch up to 100 comments at a time,
#    write comment-<id>.json
#
# 3. Iterate over the issues json files, finding which issues are pull requests.
#    For each pull request, fetch the pull request data,
#    write pr-<id>.json
#
# 4. Look at the pull request json data, and if the PR has review comments,
#    fetch up to 100 review comments at a time,
#    write pr-comment-<id>.json
#
# How long will this take?
# ========================
#
# Assuming no comments any issue or pull request,
# (and note that a pull request can be an issue, but an issue may not be a PR),
# the minimum number of API calls that the library will make is:
#
# (num issues + PRs)/100 + 0 + (num PRs) + 0
#
# Assuming one comment on each issue and pull request
# the minimum number of API calls that the library will make is:
#
# (num issues + PRs)/100 + (num issues + PRs)*2 + (num PRs) + (num PRs)*2
#
# Divide the best or worst cases total number of API requests by 5,000
# to see how many hours this will take you.

from github3 import GitHub, login, issues
import os
import argparse
import time
import datetime
import json
import glob

def writeJson(path, prefix, obj):
    fp = os.path.join(path, prefix + str(obj.id) + '.json')
    if not os.path.exists(fp):
        with open(fp, 'w') as f:
            f.write(obj.as_json())

# rate limiting resets after 1 hour (60 minutes)
GITHUB_RATELIMIT_INTERVAL = 60

# Note that the etag is absolutely useless for our initial fetching.
# An etag to fetch a particular issue doesn't change unless a new issue is
# added or an issue is updated.

def scrapeIssues(repo, repoPath, processedIssueDate):
    """Given a github repo object, create a directory structure for issues created after processedIssueDate"""
    while True:
        try:
            # We have to ask for issues in created order, because the update
            # time could change in between waiting for our rate limit to renew.
            issues = repo.issues(sort='created', direction='asc', state='all',
                                 since=processedIssueDate)
            numIssues = 0
            for i in issues:
                issuePath = os.path.join(repoPath, 'issue-' + str(i.id))
                if not os.path.exists(issuePath):
                    os.makedirs(issuePath)
                    writeJson(issuePath, 'issue-', i)
                    processedIssueDate = i.as_dict()['created_at']
                    numIssues += 1
            # FIXME: write issues etag to file to update the repo later
            break
        except:
            print('Processed', str(numIssues), 'issues')
            print('Github rate limit at',
                  str(repo.ratelimit_remaining) + ', sleeping until',
                  datetime.datetime.now() + datetime.timedelta(minutes = GITHUB_RATELIMIT_INTERVAL))
            time.sleep(60*GITHUB_RATELIMIT_INTERVAL)

def scrapeIssueComments(repo, repoPath):
    """Given a github repo object, scrape comments, ignoring issues with fetched comments."""
    # Get the list of all directories in the repoPath, looking for issue directories.
    skippedIssues = 0
    noCommentIssues = 0
    issueList = []

    # FIXME This will work if we're only using the API calls, however,
    # if this script is used in conjunction with something that uses
    # archives of github public events, we might only have some of
    # the comments on an issue.

    for f in os.listdir(repoPath):
        if not f.startswith('issue-'):
            continue
        issuePath = os.path.join(repoPath, f)
        if any(issueFile.startswith('comment-') for issueFile in os.listdir(issuePath)):
            skippedIssues += 1
        else:
            # Check the json to see if this issue has any comments.
            with open(os.path.join(issuePath, f + '.json'), 'r') as issueFile:
                numComments = int(json.load(issueFile)['comments'])
                if numComments > 0:
                    print(issuePath)
                    issueList.append(f)
                else:
                    noCommentIssues += 1

    print('Skipping', str(skippedIssues), 'issues with already fetched comments')
    print('Skipping', str(noCommentIssues), 'issues with no comments')
    print('Fetching comments for', str(len(issueList)), 'issues')

    numComments = 0
    for f in issueList:
        issueId = f.split('-')[1]
        while True:
            try:
                issuePath = os.path.join(repoPath, f)
                with open(os.path.join(issuePath, f + '.json'), 'r') as issueFile:
                    realId = json.load(issueFile)['number']
                i = repo.issue(realId)
                print(issuePath)
                # FIXME: we could hit our rate limit in between the call to grab
                # the issue and the request to get a comment.
                # We could also lose comments if there are more than 100 comments
                # (the pagination unit github3.py uses) and we hit the rate limit
                # in the middle of the for loop. The second case should be rare,
                # and the first we can catch by re-running the pass again.
                for c in i.comments():
                    print(c.id)
                    writeJson(issuePath, 'comment-', c)
                    numComments += 1
                break
            except:
                print('Processed', str(numComments), 'comments')
                print('Github rate limit at',
                      str(repo.ratelimit_remaining) + ', sleeping until',
                      datetime.datetime.now() + datetime.timedelta(minutes = GITHUB_RATELIMIT_INTERVAL))
                time.sleep(60*GITHUB_RATELIMIT_INTERVAL)

# Oddities of the github API
#
# Lesson 1:
#
# At some point, there was no API difference between issues and pull requests.
# Now, an issue can be a normal issue, or it can reference a pull request object.
#
# Any comments made on the issue are issue comments, and require two API calls
# (one to fetch the issue and the second to fetch a page of issue comments).
#
# Any comments made on the pull request commit or code are known as "review comments".
# The only way to get review comments referenced from an issue is to
# first, fetch the pull request object, and second, request the review comments.
#
# So, even through both issue comments and review comments appear on the same webpage,
# they are completely different beasts.
def scrapePullRequestComments(repo, repoPath):
    """Given a github repo object, scrape pull requests and review comments"""
    # Get the list of all directories in the repoPath, looking for issue directories.
    issueList = []
    skippedIssues = 0
   
    # Find all issues that are a pull request
    for f in os.listdir(repoPath):
        if not f.startswith('issue-'):
            continue
        issuePath = os.path.join(repoPath, f)
        if any(issueFile.startswith('pr-comment-') for issueFile in os.listdir(issuePath)):
            skippedIssues += 1
        else:
            # Check the json to see if this issue is a pull request
            with open(os.path.join(issuePath, f + '.json'), 'r') as issueFile:
                soup = json.load(issueFile)
                realId = soup['number']
                try:
                    pullRequest = soup['pull_request']
                except:
                    continue
                issueList.append((f, realId))

    print('Skipping', str(skippedIssues), 'pull requests with fetched review comments')
    print('Processing', str(len(issueList)), 'pull requests')

    numComments = 0
    for f in issueList:
        realId = f[1]
        while True:
            try:
                issuePath = os.path.join(repoPath, f[0])
                print(issuePath)
                pr = repo.pull_request(realId)
                writeJson(issuePath, 'pr-', pr)

                # Find out if this PR has any comments
                prj = json.loads(pr.as_json())
                if int(prj['comments']) == 0:
                    break
                for c in pr.review_comments():
                    print(c.id)
                    writeJson(issuePath, 'pr-comment-', c)
                    numComments += 1
                break
            except:
                print('Processed', str(numComments), 'review comments')
                print('Github rate limit at',
                      str(repo.ratelimit_remaining) + ', sleeping until',
                      datetime.datetime.now() + datetime.timedelta(minutes = GITHUB_RATELIMIT_INTERVAL))
                time.sleep(60*GITHUB_RATELIMIT_INTERVAL)

def main():
    parser = argparse.ArgumentParser(description='Scrape issues and comments from a github repository, by authenticating as a github user.')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    parser.add_argument('login', help='File storing github username and password to use for authentication (two lines)')
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)
    lastIssue = os.path.join(repoPath, 'last-processed-issue'+ '.txt')

    with open(args.login, 'r') as f:
        username = f.readline().rstrip()
        password = f.readline().rstrip()

    g = login(username, password)
    repo = g.repository(args.owner, args.repository)
    if not repo:
        print('No such repo.')
        quit()

    # Too bad makedirs exist_ok was removed in 3.4.1
    if not os.path.exists(repoPath):
        os.makedirs(repoPath)
    if repo.ratelimit_remaining != 0:
        print('Github rate limit at', str(repo.ratelimit_remaining))

    scrapeIssues(repo, repoPath, None)
    scrapeIssueComments(repo, repoPath)
    scrapePullRequestComments(repo, repoPath)

if __name__ == "__main__":
    main()


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

# Interesting examples to look at:
# rust-lang/rust/issue-176772107
# - angry user, block quotes, lists
# rust-lang/rust/issue-183154552/comment-253924506.json
# - emojis
# rust-lang/rust/issue-228842/issue-228842.json
# - inline code
# rust-lang/rust/issue-888170/comment-1257973.json
# - blocks of code
# rust-lang/rust/issue-230463/comment-421965.json
# - four space code indenting
#
# Possible other options:
# - remove breaks (lines with only ---- in them)
# - is table formatting going to be a problem?

import os
import re
import argparse
import json
import emoji
import string

def scrubFile(f):
    with open(f) as jsonFile:
        try:
            soup = json.load(jsonFile)
        except:
            return None
    text = soup.get('body')
    if not text:
        return None

    # Standardize on unix line endings.  (Yes, for whatever reason some
    # projects use Windows line endings, some unix).
    text = text.replace('\r\n', '\n')
      
    # Strip out any blockquotes or inline code
    text = re.sub('```.+?```', 'block-code.', text, flags=re.DOTALL)
    text = re.sub('`[^`]+`', 'inline-code', text, flags=re.MULTILINE)
    text = re.sub('^    .+?$', 'block-code.', text, flags=re.MULTILINE)
    # Remove any quoted text, since we want the sentiment of the person posting
    text = re.sub('^>.+?$', '', text, flags=re.MULTILINE)
    # Replace any URLs with their text
    text = re.sub('\[(.*?)\]\(.*?\)', '\g<1>', text)
    text = re.sub('https?:.+? ', 'URL ', text)
    text = re.sub('https?:.+?$', 'URL.', text, flags=re.MULTILINE)
    # convert emojis into their short hand code.
    # This makes it easier for me to correct sentiment in the training text.
    # It also allows the Standford CoreNLP to parse each emoji as a separate word,
    # which will allow us to train it for sentiment of groups of emoji.
    # E.g. :tea: is neutral, but :tea: :fire: references the "This is fine" meme
    text = emoji.demojize(text)
    # We often have blocks of code follow a colon, e.g.
    #
    # This is not correct syntax for python 3:
    # ```print foo```
    # This is the correct syntax:
    # ```print(foo)```
    #
    # This code will translate that into
    #
    # This is not correct syntax for python 3:
    # block-quote
    # This is the correct syntax:
    # block-quote
    #
    # The Standford CoreNLP assumes that the sentence continues
    # after the colon, because it's assuming sentences like
    # "Henry is the proper gentleman: charming, polite, and classy."
    #
    # We really want to consider lines that end with a : as a sentence.
    # For lines that end with an emoji, we want to add a '.' at the end.
    # Compromise and just add a '.' at the end of both.
    text = re.sub(':$', ':.', text, flags=re.MULTILINE)

    # FIXME: Standford CoreNLP doesn't parse '...' as the end of a sentence.
    # If '...' is at the end of a line, turn it into '.'
    # Does the text end with punctuation? If not, add a '.'

    # FIXME: ugh, no idea what to do with sentences that end in :)

    # FIXME: some people don't put periods after @tag someone.

    # FIXME: Ignore comments from any bots? They tend to not use punctuation.

    # FIXME: Ignore commands sent to bots

    # We can find when they do this at the end of the line.
    if text.split('\n')[-1][-1:] not in string.punctuation:
        text = text + '.'
    return text

# Create a raw text file for the issue in question
# Lines with a # are used to denote which json file the words came from
def scrubText(repoPath, issueDir):
    scrubbed = ""
    files = os.listdir(os.path.join(repoPath, issueDir))
    for f in files:
        scrubbed = scrubbed + '#' + os.path.join(issueDir, f) + '\n'
        text = scrubFile(os.path.join(repoPath, issueDir, f))
        if text:
            scrubbed = scrubbed + text + '\n.\n'
    return scrubbed

def findJsonFiles(matchedFile, searchDirs):
    matchedName, matchedExt = os.path.splitext(matchedFile)
    if not matchedExt == '.json':
        return None
    if not searchDirs:
        jsonFiles = [matchedFile]
    else:
        baseDir = os.path.dirname(matchedFile)
        try:
            jsonFiles = [os.path.join(baseDir, x) for x in os.listdir(baseDir)]
        except:
            print("WARN: Error grabbing file", matchedFile, "basedir:", baseDir)
            return None
    return jsonFiles

def findRepoJsonFiles(repoPath):
    issues = [os.path.join(repoPath, x) for x in os.listdir(repoPath)
              if x.startswith('issue-') and os.path.isdir(os.path.join(repoPath, x))]
    jsonFiles = []
    for i in issues:
        jsonFiles = jsonFiles + [os.path.join(i, x) for x in os.listdir(i)]
    return jsonFiles

# File format is relative path to json file (starting with owner/repo), one per line
def main():
    parser = argparse.ArgumentParser(description='Generate scrubbed conversation to feed into sentiment analysis')
    parser.add_argument('inFile', help='input file containing paths to json files, or (with --recurse) path to repo directory')
    parser.add_argument('outFile', help='output file')
    parser.add_argument("--dirs", help="inFile contains one or more paths to a json file; output all comments in the issue related to the given json file",
                        action="store_true", default=False)
    parser.add_argument("--recurse", help="inFile is a path to a repo; output all comments on all issues",
                        action="store_true", default=False)
    args = parser.parse_args()

    # FIXME: I think there's probably a way to make the flags exclusive?
    if args.dirs and args.recurse:
        print("Either you want to parse a file with a specific list of json paths,")
        print("or you want to parse all json files for a repo. You cannot do both.")
        return

    if not args.recurse:
        with open(args.inFile) as f:
            paths = f.read().split('\n')
    else:
        paths = [args.inFile]

    jsonCount = 0
    with open(args.outFile, 'w') as commentFile:
        for line in paths:
            if args.recurse:
                jsonFiles = findRepoJsonFiles(line)
            else:
                jsonFiles = findJsonFiles(line, args.dirs)
            if not jsonFiles:
                continue
            for json in jsonFiles:
                text = scrubFile(json)
                jsonCount = jsonCount + 1
                if text:
                    commentFile.write('#' + json + '\n')
                    commentFile.write(text)
                    commentFile.write('\n.\n')
                if (jsonCount != 0 and jsonCount % 5000 == 0):
                    print("Processed", jsonCount, "json files")

if __name__ == "__main__":
    main()

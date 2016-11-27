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
# - remove URLs

import os
import re
import argparse
import json
import emoji

# Create a raw text file for the issue in question
# Lines with a # are used to denote which json file the words came from
def scrubText(repoPath, issueDir):
    scrubbed = ""
    files = os.listdir(os.path.join(repoPath, issueDir))
    for f in files:
            with open(os.path.join(repoPath, issueDir, f)) as jsonFile:
                soup = json.load(jsonFile)
            text = soup.get('body')
            if not text:
                continue
            scrubbed = scrubbed + '#' + os.path.join(issueDir, f) + '\r\n'
            # Strip out any blockquotes or inline code
            text = re.sub('```.+?```', 'block-code', text, flags=re.DOTALL)
            text = re.sub('`[^`]+`', 'inline-code', text, flags=re.MULTILINE)
            text = re.sub('^    .+?$', 'block-code', text, flags=re.MULTILINE)
            # Remove any quoted text, since we want the sentiment of the person posting
            text = re.sub('^>.+?$', '', text, flags=re.MULTILINE)
            # Replace any URLs with their text
            text = re.sub('\[(.*?)\]\(.*?\)', '\g<1>', text)
            text = re.sub('https?:.+? ', 'URL ', text)
            text = re.sub('https?:.+?$', 'URL ', text, flags=re.MULTILINE)
            # convert emojis into their short hand code.
            # This makes it easier for me to correct sentiment in the training text.
            # It also allows the Standford CoreNLP to parse each emoji as a separate word,
            # which will allow us to train it for sentiment of groups of emoji.
            # E.g. :tea: is neutral, but :tea: :fire: references the "This is fine" meme
            text = emoji.demojize(text)
            scrubbed = scrubbed + text + '\r\n'
    return scrubbed

def main():
    parser = argparse.ArgumentParser(description='Generate scrubbed conversation to feed into sentiment analysis')
    parser.add_argument('repository', help='github repository name')
    parser.add_argument('owner', help='github username of repository owner')
    parser.add_argument('file', help='file to store processed comments')
    parser.add_argument('num', type=int, help='number of issues to process. 0 means all')
    args = parser.parse_args()

    repoPath = os.path.join(args.owner, args.repository)
    issues = [x for x in os.listdir(repoPath)
              if x.startswith('issue-') and os.path.isdir(os.path.join(repoPath, x))]
    with open(args.file, 'w') as commentFile:
        for index, i in enumerate(issues):
            commentFile.write(scrubText(repoPath, i))
            if (index % 1000 == 0):
                print("Processed", index, "issues")
            if int(args.num) > 0 and index >= int(args.num):
                break

if __name__ == "__main__":
    main()

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
# This library inserts plotly contributors graphs into html reports.

import os
import re

def getprojecthtml(htmldir, owner, repo, name):
    with open(os.path.join(htmldir, 'template', 'project-name', name)) as hfile:
        contents = hfile.read()
    # Change all instances of $PROJECT to owner/repo
    return re.sub(r'\$PROJECT', owner + '/' + repo, contents)

def overwritehtml(htmldir, owner, repo, html):
    # Create a directory owner/repo
    directory = os.path.join(htmldir, owner, repo)
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Generate the project's dashboard landing page
    index = getprojecthtml(htmldir, owner, repo, 'foss-heartbeat.html')
    with open(os.path.join(htmldir, owner, repo, 'foss-heartbeat.html'), 'w') as hfile:
        hfile.write(index)
    
    newcomers = getprojecthtml(htmldir, owner, repo, 'newcomers.html')
    for name in 'newcomers', 'responder', 'merger', 'reporter', 'reviewer':
        newcomers = re.sub('\$' + name.upper(), html[name + '-ramp'], newcomers)
    with open(os.path.join(htmldir, owner, repo, 'newcomers.html'), 'w') as hfile:
        hfile.write(newcomers)

    contributors = getprojecthtml(htmldir, owner, repo, 'contributors.html')
    for name in 'responder', 'merger', 'reporter', 'reviewer':
        contributors = re.sub('\$' + name.upper(), html[name + '-freq'], contributors)
    contributors = re.sub('\$' + 'mergetime'.upper(), html['mergetime'], contributors)
    with open(os.path.join(htmldir, owner, repo, 'contributors.html'), 'w') as hfile:
        hfile.write(contributors)

    sentiment = getprojecthtml(htmldir, owner, repo, 'sentiment.html')
    for name in 'sentimentgraph', 'sentimentstats', 'sentimentwarning':
        sentiment = re.sub('\$' + name.upper(), html[name], sentiment)
    with open(os.path.join(htmldir, owner, repo, 'sentiment.html'), 'w') as hfile:
        hfile.write(sentiment)

    # Regenerate index.html from the list of directories in docs
    # that contain heartbeat.html

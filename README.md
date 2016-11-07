# foss-heartbeat

Open source communities are made of people, who contribute in many different
ways. What makes a person more likely to continue participating in a project
and move into roles of greater responsibility?

## Identifying contributors

**foss-hearbeat** identifies seven major contribution types:

 - Issue reporter
 - Issue responder
 - Code contributor
 - Documentation contributor
 - Reviewer
 - Maintainer
 - Connector

This project uses contributor participation data (currently from GitHub) to
categorize users into these seven roles.

## Answering key contribution questions

Performing data analysis on this participation data seeks to answer
questions about what factors attract and retain those types of contributors.

While there are many different questions you could ask once you categorize
contributors and examine their contributions, the first major goal of this
project is to answer the question:

**What impact does positive or negative language have on contributor
participation?**

**foss-heartbeat** seeks to answer that question by applying sentiment
analysis on the comments community members make on others' contributions.

## Install

```bash
$ pip install -r requirements.txt
```

May require `sudo`.

## Usage

### Scrape information from GitHub

First, scrape information from GitHub for each repository you're analyzing.

```bash
$ python ghscraper.py GITHUB_REPO_NAME GITHUB_OWNER_NAME FILE_WITH_CREDENTIALS
```

Or if you prefer not to type your password into a file, or have turned on two-factor authentication for your GitHub account, use an access token instead:

```bash
$ python ghscraper.py GITHUB_REPO_NAME GITHUB_OWNER_NAME GITHUB_OAUTH_TOKEN
```

(Make sure to select the following scopes for your token: `public_repo`)

### Categorize

Then categorize the data.

```bash
$ python ghcategorize.py GITHUB_REPO_NAME GITHUB_OWNER_NAME
```

### Stats

Then generate statistics.

```bash
$ python ghstats.py GITHUB_REPO_NAME GITHUB_OWNER_NAME docs/
```


### Report

Now generate a report to visualize the categorized stats data.

```bash
$ python ghreport.py foo bar
```

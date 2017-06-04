# foss-heartbeat

Open source communities are made of people, who contribute in many different
ways. What makes a person more likely to continue participating in a project
and move into roles of greater responsibility?

## Identifying contributors

**foss-heartbeat** identifies seven major contribution types:

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

If you don't have Python installed, follow the instructions in the
[Django Girls installation guide](https://tutorial.djangogirls.org/en/python_installation/).

Clone the repository, change to the directory containing the repository.

```bash
$ pip install -r requirements.txt
```

May require `sudo`. If `sudo` fails, try passing the `--user` flag.

## Install Stanford CoreNLP

Stanford CoreNLP includes natural language processing and a neural network (a
type of machine learning tool) that can learn how to recognize sentiment at a
sentence level.

These installation directions are slightly expanded upon from the installation
directions at http://stanfordnlp.github.io/CoreNLP/index.html#download.
    
Clone the git repo:

```bash
$ git clone git@github.com:stanfordnlp/CoreNLP.git
```
    
Copy the default sentiment models into the liblocal directory:
```bash
$ cd CoreNLP/liblocal
$ wget http://nlp.stanford.edu/software/stanford-corenlp-models-current.jar
$ wget http://nlp.stanford.edu/software/stanford-english-corenlp-models-current.jar
```

(Note: the directions on the Stanford CoreNLP for how to set the classpath
didn't work for me. Instead, I used the `-Djava.ext.dirs=lib:liblocal` flag to
point Java to the sentiment models I placed in CoreNLP/liblocal.)

## Usage

### Scrape information from GitHub

First, scrape information from GitHub for each repository you're analyzing.
Note that this step may require several hours or even a day, due to GitHub
API rate limits.

```bash
$ python ghscraper.py GITHUB_REPO_NAME GITHUB_OWNER_NAME FILE_WITH_CREDENTIALS
```

If you prefer not to type your password into a file, or have turned on two-factor authentication for your GitHub account, use an access token instead:

```bash
$ python ghscraper.py GITHUB_REPO_NAME GITHUB_OWNER_NAME GITHUB_OAUTH_TOKEN
```

(Make sure to select the following scopes for your token: `public_repo`.)

### Categorize

Next, run the script to categorize GitHub interactions into different types
of open source contributions:

```bash
$ python ghcategorize.py GITHUB_REPO_NAME GITHUB_OWNER_NAME
```

### Stats

Then generate HTML reports with statistics (note that this imports functions from ghreport.py):

```bash
$ python ghstats.py GITHUB_REPO_NAME GITHUB_OWNER_NAME docs/
```

The HTML report will be created in ```docs/GITHUB_OWNER_NAME/GITHUB_REPO_NAME```.
You will need to hand-edit [`docs/index.html`](https://github.com/sarahsharp/foss-heartbeat/blob/master/docs/index.html)
to link to ```docs/GITHUB_OWNER_NAME/GITHUB_REPO_NAME/foss-heartbeat.html```.

### (Optional) Train the Stanford CoreNLP sentiment model

Sentiment analysis relies on being trained with a large set of sentences that
are relevant to the text you want to study. For example, hand-analyzed
sentences from one open source project may be used to train the sentiment model
to automatically analyze another project.

The Stanford CoreNLP sentiment models are trained on movie reviews and aren't
very good for analyzing sentiment of code reviews. They tend to look at the
sentence structure of technical comments and rank them as a negative tone, even
if there are no negative words. They're also not trained for curse words or
emojis.

The Stanford CoreNLP includes a way to retrain the neural network to recognize
sentiment of sentence structures. You have to feed it a training set (their
training set is ~8,000 sentences) and a development set that helps you tune
parameters of the neural net. Both sets have to be sentences that are manually
turned into Penn Tree format.

You can find FOSS Heartbeat's training set in [`empathy-model/train.txt`](https://github.com/sarahsharp/foss-heartbeat/blob/master/empathy-model/train.txt) and its development set in [`empathy-model/dev.txt`](https://github.com/sarahsharp/foss-heartbeat/blob/master/empathy-model/dev.txt).

The sentences in the training model are taken from open source projects: LKML,
Debian-devel mailing list, glibc, AngularJS, .NET, Elm, React, Fsharp, Idris,
jQuery, VS Code, Node.js, Rails, Rust, Servo, and Bootstrap.

There are around 10-20 simple sentences that I hoped would help train the
model. I've also included sentiment for all the curse words found at
http://www.noswearing.com/dictionary and all the short-hand codes for emojis at
http://www.webpagefx.com/tools/emoji-cheat-sheet/.

If you make changes to train.txt and dev.txt, you can retrain the model:

```bash    
$ cd path/to/CoreNLP
$ java -cp stanford-corenlp.jar -Djava.ext.dirs=lib:liblocal -mx5g \
    edu.stanford.nlp.sentiment.SentimentTraining -numHid 25 \
    -trainPath path/to/foss-heartbeat/empathy-model/training.txt \
    -devPath path/to/foss-heartbeat/empathy-model/dev.txt -train \
    -model path/to/foss-heartbeat/empathy-model/empathy-model.ser.gz
```

### Running the sentiment model in stdin mode

In the CoreNLP directory, you can run a test of the default sentiment model.
This parses sentences from stdin after you hit enter, but be aware that it returns
one line for multiple lines fed into it at once, rather than using the sentence
parser like the -file option does.
    
```bash
$ cd path/to/CoreNLP
$ java -cp stanford-corenlp.jar -Djava.ext.dirs=lib:liblocal \
  -mx5g edu.stanford.nlp.sentiment.SentimentPipeline -stdin -output pennTrees
```

`-mx5g` specifies that 5GB is the maximum amount of RAM to use.

`-output pennTrees` specifies that the Stanford CoreNLP output the full
sentence sentiment analysis. To get an idea of what the format means, take a
look at [the live demo](http://nlp.stanford.edu:8080/sentiment/rntnDemo.html).
Removing that flag will change the output mode to only stating the overall
sentence tone (very negative, negative, neutral, positive, very positive).

If you wish to run the sentiment analysis using FOSS Heartbeat's empathy model,
you should instead run:

```bash
$ cd path/to/CoreNLP
$ java -cp stanford-corenlp.jar -Djava.ext.dirs=lib:liblocal -mx5g \
    edu.stanford.nlp.sentiment.SentimentPipeline -stdin \
    -sentimentModel path/to/foss-heartbeat/empathy-model/empathy-model.ser.gz \
    -output pennTrees
```

[`language/substitutions.txt`](https://github.com/sarahsharp/foss-heartbeat/blob/master/language/substitutions.txt) contains a list of word sentiment labels that need
to be relabeled from the default Stanford CoreNLP Penn Tree output. The Stanford
CoreNLP default model was trained on movie reviews, so it incorrectly labels
words we find in software development conversation. For example, 'Christian' is
labeled as positive, since people may leave a review about the positivity of
Christian movies; in software development, 'Christian' is most likely someone's
name. Since FOSS Heartbeat's model is trained to recognize empathy and praise
as positive, and personal attacks as negative, we often have to shift the
sentiment of specific words.

You can use `substitutions.txt` to change word sentiment labels in the sentences
from the default sentiment model. It involves stripping the '%' off the Vim
substitution commands in `substitutions.txt`, using the resulting file as a sed
regular expression file, and piping the output from the sentiment model into
sed:

```bash
$ cd path/to/CoreNLP
$ cat path/to/foss-heartbeat/language/substitutions.txt | \
    sed -e 's/^%//' > /tmp/subs.txt; \
    java -cp stanford-corenlp.jar -Djava.ext.dirs=lib:liblocal -mx5g \
    edu.stanford.nlp.sentiment.SentimentPipeline -stdin -output pennTrees | \
    sed -f /tmp/subs.txt
```

Once this is done, you can feed interesting examples in and put them in
`empathy-model/train.txt` or `empathy-model/dev.txt` to retrain FOSS Heartbeat's model. You
will need to manually propagate up any sentiment changes from the innermost
sentence fragments to the root of the sentence. This is something that needs to
be done by human eyes, since the sentence tone can change when different
sentence fragments are combined.

### Scrub comments for sentiment analysis

In order to cut down on the amount of time that the Stanford CoreNLP has to
process sentences, we need to drop any inline code that is (most likely) to be
ranked as neutral, or may be miscategorized because the model hasn't been
trained on that particular language.

We also convert any Unicode emojis into their short-hand codes (as described at
http://www.webpagefx.com/tools/emoji-cheat-sheet/), which makes it easier on
humans to read analyzed plain-text sentences.

It also takes time for the Stanford CoreNLP to load the models. It is faster
to write a bunch of text to a file and use the `-file` command line option to
parse a file, than to re-run the command for each sentence. Thus, there is a
FOSS Heartbeat script that generates a scrubbed file of all comments in a repo
that you can feed to Stanford CoreNLP.

The output file will contain the filenames (preceded by a hashmark) and the
contents of the scrubbed comments. Sentences may span multiple lines, and the
Stanford CoreNLP will break them up using its sentence parser. It does mean
that things like lists or sentences that don't end with punctuation will get
joined with the next line.

To generate the scrubbed file, run:

```bash
$ python ../src/ghsentiment.py owner/repo/ owner/repo/all-comments.txt --recurse
```

### Run the scrubbed data through the sentiment analysis

To use FOSS Heartbeat's retrained empathy model on the scrubbed comments file, run:

```bash
$ cd path/to/CoreNLP
$ java -cp stanford-corenlp.jar -Djava.ext.dirs=lib:liblocal -mx5g \
    edu.stanford.nlp.sentiment.SentimentPipeline -output pennTrees \
    -sentimentModel path/to/foss-heartbeat/empathy-model/empathy-model.ser.gz \
    -file path/to/owner/repo/all-comments.txt > \
    path/to/owner/repo/all-comments.empathy.txt
```

### Modifying the sentiment training data

In order to retrain the sentiment model, you need to add parsed sentences with
Penn Tree sentiment for each word. You'll need to add about one sentence to
`empathy-model/dev.txt` for every eight similar sentences you add to `empathy-model/train.txt`.

Penn Tree sentence format initially looks very strange:

```
(4 (2 Again) (4 (2 this) (4 (4 (2 is) (4 (4 super) (3 (3 great) (2 work)))) (2 .))))
```

Each word, and each combined sentence part, has an associated sentiment from zero
to four. In the empathy model, the following categorizations are used:

 - 4 (Very positive): Thank yous with emphasis (*great* or great!), or specific praise
 - 3 (Positive): Thanks, praise, encouragement, empathy, helping others, and apologies
 - 2 (Neutral): Any talk about code that includes opinions without expressing gratitude, empathy, cursing, or discriminatory language
 - 1 (Negative): Comments about code or people with mild cursing or abelist language
 - 0 (Very Negative): Comments with strong cursing, sexist, racist, homophobic, transphobic, etc. language

It can sometimes be easier to see how sentence sentiment changes as its parsed
phrases are combined, by putting it in a tree format:

```
(4
   (2 Again)
   (4
      (2 this)
      (4
         (4
            (2 is)
            (4
               (4 super)
               (3
                  (3 great)
                  (2 work))))
         (2 .))))
```

There's a [good visualization tool by the Standford CoreNLP
developers](http://nlp.stanford.edu:8080/sentiment/rntnDemo.html), but it is not
open source and uses the default sentiment model trained on movie reviews.

#### Vim Tips and Tricks

In order for people to better "see" the sentiment in Penn Tree text files, you
can use [this Vim plugin to highlight the sentiment
labels](http://vim.wikia.com/wiki/Highlight_multiple_words). You'll need to
modify the plugins/highlight.csv files to have the following lines:

```
6,black,yellow,black,yellow
7,white,DarkRed,white,firebrick
8,white,DarkGreen,white,DarkGreen
9,white,DarkBlue,white,DarkSlateBlue
```

When you open a Penn Tree file, you can run the following commands to highlight
sentiment:

```
Highlight 7 0
Highlight 6 1
Highlight 9 3
Highlight 8 4
```

Most open source code talk is neutral, so I don't bother to highlight the 2
sentiment.

Additionally, when comparing the sentiment results from two different models,
it's useful to have vimdiff only highlight the individual words (or in our
case, the sentiment labels) that have changed, rather than highlighting the
whole line. [This Vim plugin highlights only changed words when Vim is in diff
mode.](https://github.com/rickhowe/diffchar.vim)

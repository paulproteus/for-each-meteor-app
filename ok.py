#!/usr/bin/python
import os
import treq
import capnp
import uuid
capnp.remove_import_hook()
meteor_app_capnp = capnp.load('meteor-app.capnp')

# Make sure that we will be able to access GitHub.
assert os.environ.get('GITHUB_TOKEN'), "You need a GitHub token in your environment."

def get_applist(DATA_PATH='data'):
    data = []
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, 'rb') as fd:
            data = meteor_app_capnp.AppList.read(fd).data

    return data.sort(key=lambda thing: thing.starsCount)

def save_applist(applist, DATA_PATH='data'):
    applist.data = data.sort(key=lambda thing: thing.starsCount)
    with open(DATA_PATH, 'w+b') as fd:
        applist.write(fd)

def make_github_search_url():
    url = ('https://paulproteus:' + os.environ['GITHUB_TOKEN'] +
           '@api.github.com/search/repositories?q=meteor&sortby=stars&per_page=10')
    return url

def do_search():
    url = make_url()
    return requests.get(url).json()

def github_urls_from_search_results(results):
    return [x['html_url'] for x in results['items']]

# Use raw.githubusercontent.com to look for a .meteor/ directory. Note
# that its absence does not mean the thing is not a Meteor app; this
# could be a false negative. We should do a fresh pass via GitHub
# search for the negatives.
def looks_like_a_meteor_app(github_url):
    githubusercontent

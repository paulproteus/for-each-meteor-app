#!/usr/bin/python
import os
import requests
import capnp
import uuid
import tempfile
import lxml.html
import urlparse
import logging
import subprocess
import scandir
capnp.remove_import_hook()
meteor_app_capnp = capnp.load('meteor-app.capnp')

import contextlib
import os


def github_url_to_dir_name(github_url):
    without_github_dot_com = github_url.replace('https://github.com/', '')
    assert github_url.count('/') == 1
    return without_github_dot_com.replace('/', '.')


@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

# Make sure that we will be able to access GitHub.
assert os.environ.get('GITHUB_TOKEN'), "You need a GitHub token in your environment."

def main(max_package_attempts=None):
    assert os.environ.get('GIT_REPO_URL'), "You need the git repo URL in your environment."
    assert os.path.exists('/usr/bin/markdown'), "You need to have a markdown renderer installed."

    # If our state directory does not exist, do a fresh git clone.
    if not os.path.exists('state'):
        subprocess.check_call(['git', 'clone', os.environ.get('GIT_REPO_URL'), 'state'])
        # Make sure someone has set up the directory correctly.
        assert os.path.exists('state/data.md'), "You need to make data.md, which we use as an ad-hoc data store."

    # Loop across GitHub results for Meteor apps. Attempt to turn them
    # into SPKs.
    n = 0
    for github_url in iterator_across_meteor_apps_on_github():
        n += 1

        # Only attempt to package this if it looks like we haven't
        # packaged it already.
        if github_url_seems_present_in_state(github_url):
            continue

        try:
            make_package(github_url)
        except Exception:
            logging.exception()
        if (max_package_attempts is not None) and (n >= max_package_attempts):
            return

def github_url_seems_present_in_state(github_url):
    # Make assertions that the GitHub URL seems canonical enough
    # to be worth checking for.
    #
    # "Accidentally" quadratic. Life is short, or something.
    with open('state/data.md') as fd:
        s = fd.read()
        return github_url in s

def make_package(github_url):
    # General strategy:
    #
    # - Clone the app to a fresh dir in /tmp with a name inspired by
    #   the git repo name.
    #
    # - Find the '.meteor' directory and cd into its parent.
    #
    # - Do vagrant-spk auto.
    #
    # - See if a package came out.
    #
    # - Record that we tried in "state". Leave the SPK on the
    #   filesystem. hopefully vagrant-spk gave it a nice filename.
    prefix = github_url_to_dir_name(github_url)
    with working_directory(tempfile.mkdtemp(prefix=prefix)):
        print os.getcwd()
        subprocess.check_call(['git', 'clone', github_url])
        # Find the .meteor dir and cd into its parent.
        found_meteor_dir = False
        for scandir_result in scandir.walk('.'):
            name = scandir_result[0]
            if name.endswith('/.meteor'):
                found_meteor_dir = True
                os.chdir(name[:-len('.meteor')])
        assert found_meteor_dir, "Could not find Meteor directory. Bailing out."
        # TODO: In vagrant-spk auto meteor, hack out Cordova stuff.
        environ = dict(os.environ)
        environ['VAGRANT_SPK_EXPERIMENTAL'] = 'Y'
        try:
            subprocess.check_call(['vagrant-spk', 'auto', 'meteor'],
                                  env=environ)
        finally:
            # Well, it worked or not. Destroy the VM because life is short.
            subprocess.check_call(['vagrant-spk', 'destroy'])
        # TODO:
        #
        # - Use the GitHub repo name somewhere in the sandstorm-pkgdef.capnp metadata
        #
        # - Use that in the *.spk filename too
        #
        # - Have some way to avoid re-packaging things that already were packaged,
        #   so I can stop & start this process.
        #
        #     - One way to do that is to store the info in a git repository...
        #       ... along with the working SPKs... in a Markdown format... that
        #       I can auto-convert into HTML.

def make_github_web_search_url_for_meteor_apps(page_num):
    url = 'https://github.com/search?o=desc&q=path:.meteor+browser+server%22This+file+contains+information+which+helps+Meteor+properly+upgrade+your%22&ref=searchresults&s=indexed&type=Code&utf8=%E2%9C%93'
    url += '&={0}'.format(page_num)
    return url

def make_github_search_url():
    url = ('https://paulproteus:' + os.environ['GITHUB_TOKEN'] +
           '@api.github.com/search/repositories?q=meteor&sortby=stars&per_page=100')
    return url

def iterator_across_known_good_meteor_apps_on_github():
    for item in ['https://https://github.com/HelloMeteorBook/2015GlobalHackathon']:
        yield item

def iterator_across_meteor_apps_on_github():
    page_num = 1
    while page_num <= 100:
        response_bytes = get_search_response(page_num)
        results = get_matching_github_urls(response_bytes)
        for item in results:
            yield item
        current_page += 1

def get_search_response(page_num=1):
    # TODO: Turn into a generator.
    url = make_github_web_search_url_for_meteor_apps(page_num)
    response = requests.get(url)
    return response.content

def get_matching_github_urls(response_bytes):
    parsed = lxml.html.document_fromstring(response_bytes)
    return [urlparse.urljoin('https://github.com/', x.attrib.get('href'))
            for x in parsed.cssselect('p.title a:first-child')]

def github_urls_from_search_results(results):
    return [x['html_url'] for x in results['items']]

# Use raw.githubusercontent.com to look for a .meteor/ directory. Note
# that its absence does not mean the thing is not a Meteor app; this
# could be a false negative. We should do a fresh pass via GitHub
# search for the negatives.
def looks_like_a_meteor_app(github_url):
    githubusercontent

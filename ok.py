#!/usr/bin/python
import os
import requests
import uuid
import tempfile
import lxml.html
import urlparse
import logging
import subprocess
import scandir

import contextlib
import os


ORIG_CWD = os.getcwd()
STATE_PATH = os.path.join(ORIG_CWD, 'state')


def github_url_to_dir_name(github_url):
    without_github_dot_com = github_url.replace('https://github.com/', '')
    assert without_github_dot_com.count('/') == 1, without_github_dot_com
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

def main(max_package_attempts=None, url_generator_callable=None):
    if url_generator_callable is None:
        url_generator_callable = iterator_across_meteor_apps_on_github
    assert os.environ.get('GIT_REPO_URL'), "You need the git repo URL in your environment."
    assert os.path.exists('/usr/bin/markdown'), "You need to have a markdown renderer installed."

    # If our state directory does not exist, do a fresh git clone.
    if not os.path.exists(STATE_PATH):
        subprocess.check_call(
            ['git', 'clone', os.environ.get('GIT_REPO_URL'), STATE_PATH],
            cwd=ORIG_CWD,
       )
    else:
        # Make sure the state directory is up to date.
        subprocess.check_call(['git', 'push', '-q'],
                              cwd=STATE_PATH)
        subprocess.check_call(['git', 'pull', '--rebase'],
                              cwd=STATE_PATH)
        subprocess.check_call(['git', 'push', '-q'],
                              cwd=STATE_PATH)

    # Loop across GitHub results for Meteor apps. Attempt to turn them
    # into SPKs.
    n = 0
    for github_url in url_generator_callable():
        n += 1

        # Only attempt to package this if it looks like we haven't
        # packaged it already.
        if github_url_seems_present_in_state(github_url):
            print 'Skipping', github_url, 'because we already tried it.'
            continue

        try:
            make_package(github_url)
        except Exception as e:
            logging.exception(e)
        if (max_package_attempts is not None) and (n >= max_package_attempts):
            return

def github_url_seems_present_in_state(github_url):
    as_path = github_url_to_dir_name(github_url)
    return os.path.exists(os.path.join(STATE_PATH, as_path))


def save_state_of_this_github_repo(github_url, packagingSuccessful):
    as_path = github_url_to_dir_name(github_url)
    as_abspath = os.path.join(os.path.join(STATE_PATH, as_path))
    with open(as_abspath, 'w') as fd:
        fd.write(unicode(int(packagingSuccessful)))
    subprocess.check_call(['git', 'add', '.'], cwd=STATE_PATH)
    subprocess.check_call(['git', 'commit', '-m', 'autocommit', '--allow-empty'], cwd=STATE_PATH)
    subprocess.check_call(['git', 'push', '-q'], cwd=STATE_PATH)


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
    prefix = github_url_to_dir_name(github_url) + '.'
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
        success = False
        try:
            if not environ.get('DRY_RUN'):
                subprocess.check_call(['vagrant-spk', 'auto', 'meteor'],
                                      env=environ)
            success = True
        finally:
            if not environ.get('DRY_RUN'):
                subprocess.check_call(['vagrant-spk', 'destroy'])
                # Well, it worked or not. Destroy the VM because life is short.

            # Always store a note in "state/data.md" indicating that
            # we attempted to auto-package this thing, and how it
            # went.
            save_state_of_this_github_repo(
                github_url, packagingSuccessful=success)

def make_github_web_search_url_for_meteor_apps(page_num):
    url = 'https://github.com/search?o=asc&q=path:.meteor+browser+server&s=indexed&type=Code&utf8=%E2%9C%93'
    url += '&={0}'.format(page_num)
    return url

def iterator_across_known_good_meteor_apps_on_github():
    for item in ['https://github.com/HelloMeteorBook/2015GlobalHackathon']:
        yield item

def iterator_across_meteor_apps_on_github():
    # TODO: Do other searches and union them all.
    page_num = 1
    while page_num <= 100:
        response_bytes = get_search_response(page_num)
        results = get_matching_github_urls(response_bytes)
        for item in results:
            yield item
        page_num += 1

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

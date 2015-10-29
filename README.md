## Design notes

* This code uses `treq` for making requests.

* It makes requests in the following way:

    * At process start time, read in any capnproto data.

    * Use GitHub web search to get the list of Meteor apps.

    * Use the GitHub API to get the # of stars for those repositories.

    * Store this info in a list of Cap'n Proto structs in memory.

    * At process stop time, save that to disk.

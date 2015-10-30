#!/bin/bash
sudo apt-get build-dep python-lxml
if [ -e env/bin/pip ] ; then
  env/bin/pip install -r requirements.txt
fi

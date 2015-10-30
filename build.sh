#!/bin/bash
sudo apt-get build-dep python-lxml python-cryptography
if [ -e env/bin/pip ] ; then
  env/bin/pip install -r requirements.txt
fi

#!/bin/sh
PYMISCID_VERSION=`cat VERSION`
sh ./clean.sh
git clone ssh://oberon/git/mercier/codebench.git
cd ..
tar c ./pymiscid --exclude=*.git | gzip > "pymiscid-${PYMISCID_VERSION}.tar.gz"

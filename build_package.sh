#!/bin/sh
PYMISCID_VERSION=`cat VERSION`
sh ./clean.sh
cd ..
tar c ./pymiscid --exclude=*.git | gzip > "pymiscid-${PYMISCID_VERSION}.tar.gz"

#!/bin/sh

cd ./doc
make clean
cd ..
find . -name *.pyc -delete
for file in codebench build dist PyMiSCID.egg-info .build pymiscid/.build pymiscid/.ssh; do
    if [ -e $file ]; then
	rm -rf $file
    fi
done


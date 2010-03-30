#!/bin/sh
DIR="pymiscid/codebench"
FILES="events.py wref.py xml.py generator.py decorators.py"
rm -rf ${DIR}
mkdir ${DIR}
for file in ${FILES}
do
    echo "copying ${file} from codebench"
    cp ../codebench/${file} ${DIR}
done
touch ${DIR}/__init__.py



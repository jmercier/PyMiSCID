#!/bin/sh
zip -r plasmoid.zip contents icon.png metadata.desktop
plasmapkg -r plasmoid.zip
plasmapkg -i plasmoid.zip
rm plasmoid.zip

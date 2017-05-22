#!/bin/csh -f

cd /IMAGESETS
sudo rsync -aP --links --delete diskstation:/volume1/homes/$USER/Public/Imagesets/DVIADetDB/ DVIADetDB/

#!/bin/csh -f

if ($#argv != 2) then
  echo "Usage: `basename $0` <path-to-kitti-db-input> <path-to-new-voc-db-output>"
  exit(1)
endif
set kitti = $argv[1]
set voc   = $argv[2]
echo "kitti = $kitti"
echo "voc = $voc"


set cmd = ( python3 ${HOME}/Projects/vod-converter/vod_converter/main.py --from kitti --from-path ${kitti} --to voc --to-path ${voc} )
echo $cmd
$cmd

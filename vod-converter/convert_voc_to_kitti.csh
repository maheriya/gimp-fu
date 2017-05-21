#!/bin/csh -f

if ($#argv != 2) then
  echo "Usage: `basename $0` <path-to-voc-db-input> <path-to-new-kitti-db-output>"
  exit(1)
endif
set voc   = $argv[1]
set kitti = $argv[2]
echo "voc = $voc"
echo "kitti = $kitti"


set cmd = ( python3 ${HOME}/Projects/vod-converter/vod_converter/main.py --from voc --from-path ${voc} --to kitti --to-path ${kitti} )
echo $cmd
$cmd

#! /usr/bin/env python
## This script converts PNG files to JPEG

import sys
import os
from os import listdir, getcwd
from os.path import join
from PIL import Image


######### main #########
wd = getcwd()

filename = sys.argv[1]
in_file = open('%s/%s'%(wd, filename))
#print("Shiva 1")
for images in in_file:
    if not os.path.exists('%s/JPEGImages/'%(wd)):
        os.makedirs('%s/JPEGImages/'%(wd))
    print images
    Image.open('%s/PNGImages/%s.png'%(wd, images.strip())).save(('%s/JPEGImages/%s.jpg'%(wd, images.strip())), "JPEG")

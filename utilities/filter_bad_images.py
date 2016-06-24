#!/usr/bin/env python
#
## Don't use this script. Work in progress (and doesn't work on files that downloaded without error but are wrong)
import os, sys
import re

if len(sys.argv) != 2:
    print("Usage: filter_bad_images.py <wget_log_file>")
    sys.exit(1)

lfile = os.path.realpath(sys.argv[1])
basedir = os.path.dirname(lfile)
# The log file names must be named wget_{srcdir}.log. E.g. wget_n04297847-stair-carpet.log
srcdir = re.sub(r'wget_(.*).log', r'\1', os.path.basename(lfile))
print("Finding bad images in download directory {}".format(srcdir))
with open(lfile, 'r') as f:
    while True:
        l = f.readline().strip()
        if l.startswith('FINISHED'):
            break

#         if l.startswith('2016') and 'URL:' in l:
#             continue # skip good images
#         if 'unable to resolve' in l:
#             continue
#         if 'Read error' in l:
#             continue
        if 'URL:' in l and '/404.gif' in l: # special case of, e.g., tinypic.com which doesn't give error but sends this gif
            #-> "n04297847-stair-carpet/o5153r.jpg"
            img = re.sub(r'-> "{}/(.*)"'.format(srcdir), r'\1', l)
            img = os.path.basename(img)
            print('Found bad image [404.gif]: {}'.format(img))
            continue
        if l.startswith('http?://'):
            img = os.path.basename(l)
            img = re.sub(r':', '', img)
            l = f.readline().strip()
            
        

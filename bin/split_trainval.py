#! /usr/bin/env python
#
#   File = split_trainval.py (based on merge_image_lists.py)
#   Splits image lists to create VOC style train and val lists
#
############################################################################
#
import sys, os
import glob
import random
import re

## Run this in the 'png' directory where other links are already created appropriately.
## For example, 'png' directory may look like following (from ls -l output):
##  Annotations -> ../Annotations/
##  1_stair     -> ../augmented/1_stair/
##  2_curb      -> ../augmented/2_curb/
##  3_doorframe -> ../augmented/3_doorframe/
##
def openLabels():

    ###
    imgsetsdir = 'ImageSets'  ## This will be created to save train.txt and val.txt
    vlabels = []
    tlabels = []

    filelist = glob.glob('./*/labels.txt')
    print("Files: {}".format(filelist))
    labels = []
    for filename in filelist:
        dname = os.path.dirname(filename).split('/')[-1]
        #print dname
        filePtr = open(filename, 'r')
        for line in filePtr.readlines():
            img = line.strip().split()[0]
            label = '.'.join(img.split('.')[:-1]) ## Remove extension
            labels.append(os.path.join(dname,label))
    print 'Found {} labels.'.format(len(labels))
                      
    random.shuffle(labels)
    nval = int(len(labels)*0.1)
    print ("Validation labels to make: {}".format(nval))
    cval = 0
    while(cval<nval):
        random_index = random.randrange(0, (len(labels)-1))
        # Handle augmented images: Once an image is selected, select all related augmented images too.
        imgindex = labels[random_index].split('_')[0:4]  ## For names containing id_class (e.g. 1_stair/1_stair_00000_09_pan2.png)
        imgindex = '_'.join(imgindex)
        print 'Selected for val: {}'.format(imgindex)

        for l in labels:
            if re.search(imgindex, l):
                cval = cval + 1
                vlabels.append(l)
                labels.remove(l)

    tlabels = labels
    print 'Created {t} train and {v} val labels.'.format(v=len(vlabels), t=len(tlabels))
    random.shuffle(tlabels)
    random.shuffle(vlabels)
    if not os.path.exists(imgsetsdir):
        os.makedirs(imgsetsdir)
    outFile = open(os.path.join(imgsetsdir, 'train.txt'), 'w')
    outFile.write('\n'.join(tlabels))
    outFile.close()
    outFile = open(os.path.join(imgsetsdir, 'val.txt'), 'w')
    outFile.write('\n'.join(vlabels))
    outFile.close()
    
openLabels()

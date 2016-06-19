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

if len(sys.argv) != 2:
    print '\nUsage split_trainval.py <full/path/to/labels_file.txt>\n'
    sys.exit(1)

labels_file = os.path.realpath(sys.argv[1])

if not os.path.exists(labels_file):
    print 'Labels file {} does not exist!'
    sys.exit(1)

def openLabels(labels_file):
    ###
    pngdir  = os.path.dirname(labels_file)
    pngdir  = '/'.join(pngdir.split('/')[:-1])
    imgsetsdir = os.path.join(pngdir, 'ImageSets')
    vlabels = []
    tlabels = []
    filePtr = open(labels_file, 'r')
    labels = []
    for line in filePtr.readlines():
        img = line.strip().split()[0]
        labels.append('.'.join(img.split('.')[:-1]))
    print 'Found {} labels.'.format(len(labels))
                      
    random.shuffle(labels)
    nval = int(len(labels)*0.1)
    print ("Validation labels to make: {}".format(nval))
    cval = 0
    while(cval<nval):
        random_index = random.randrange(0, (len(labels)-1))
        # Handle augmented images: Once an image is selected, select all related augmented images too.
        imgindex = labels[random_index].split('_')[0:3]  ## For names containing id_class (e.g. 0_catchall_00000_09_pan2.png)
        #imgindex = labels[random_index].split('_')[0:1]   ## For names not containing id_class (e.g., 00007_09_pan2.png)
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
    
openLabels(labels_file)

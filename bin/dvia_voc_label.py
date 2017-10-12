#! /usr/bin/env python
## Shiva : I picked this file from darknet/scripts and modified for DVIA

import xml.etree.ElementTree as ET
import pickle
import os
from os import listdir, getcwd
from os.path import join

## I don't need this
##sets=[('2012', 'train'), ('2012', 'val'), ('2007', 'train'), ('2007', 'val'), ('2007', 'test')]

## This is VOC dataset, I am subsituting cow to stair, and sheep to door. By doing this I am aware that I am changing the organic classes to inorganic classes. Let's us see
##classes = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
image_sets = ["stair", "doorframe"]
classes = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "stair", "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "doorframe", "sofa", "train", "tvmonitor"]


def convert(size, box):
    dw = 1./(size[0])
    dh = 1./(size[1])
    x = (box[0] + box[1])/2.0 - 1
    y = (box[2] + box[3])/2.0 - 1
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x*dw
    w = w*dw
    y = y*dh
    h = h*dh
    return (x,y,w,h)

def convert_annotation(wd, image_id):
    in_file = open('%s/Annotations/%s.xml'%(wd, image_id))
    out_file = open('%s/labels/%s.txt'%(wd, image_id), 'w')
    tree=ET.parse(in_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)

    for obj in root.iter('object'):
        cls = obj.find('name').text
        if cls not in classes:
            continue
        cls_id = classes.index(cls)
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text), float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
        bb = convert((w,h), b)
        out_file.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + '\n')


######### main #########
wd = getcwd()

for image_set in image_sets:
    if not os.path.exists('%s/labels/'%(wd)):
        os.makedirs('%s/labels/'%(wd))
    image_ids = open('%s/ImageSets/%s.txt'%(wd, image_set)).read().strip().split()
    list_file = open('%s_dvia_voc.txt'%(image_set), 'w')
    print (image_ids)
    print (list_file)
    i=0
    for image_id in image_ids:
        list_file.write('%s/JPEGImages/%s.jpg\n'%(wd, image_id))
        print image_id
        convert_annotation(wd, image_id)
        print('Shiva: converted %d image'%(i))
        i += 1
    list_file.close()


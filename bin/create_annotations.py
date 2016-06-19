#! /usr/bin/env python
#
# This script converts a labels file under a PNG directory
# and converts it into VOC compatible XML annotation files (one per image).
#
############################################################################
#
import sys, os
from glob import glob
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment
from xml.dom import minidom

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def addFileName(top, fname):
    filename = SubElement(top, 'filename')
    filename.text = fname
    
def addSize(top, w, h, d):
    el_size        = SubElement(top, 'size')
    el_size_w      = SubElement(el_size, 'width')
    el_size_w.text = str(w)
    el_size_h      = SubElement(el_size, 'height')
    el_size_h.text = str(h)
    el_size_d      = SubElement(el_size, 'depth')
    el_size_d.text = str(d)

def addObject(top, name, bb):
    object = SubElement(top, 'object')
    object_name             = SubElement(object, 'name')
    object_name.text        = name
    object_bndbox           = SubElement(object, 'bndbox')
    object_bndbox_xmin      = SubElement(object_bndbox, 'xmin')
    object_bndbox_xmin.text = bb[0]
    object_bndbox_ymin      = SubElement(object_bndbox, 'ymin')
    object_bndbox_ymin.text = bb[1]
    object_bndbox_xmax      = SubElement(object_bndbox, 'xmax')
    object_bndbox_xmax.text = bb[2]
    object_bndbox_ymax      = SubElement(object_bndbox, 'ymax')
    object_bndbox_ymax.text = bb[3]

def createAnnotations(labels_file, width, height):
    """Registered function; Creates XML annotations in 'Annotations' directory parallel to the labels dir.
    labels_file : The full path to the labels_NP_MLC.txt file.
    width  : width of all images
    height : height of all images
    This script only works with NC_MLC format:
    <filename> <mlc_classes> <np0[np1[...]]> <bb0[bb1[bb2]]>
    We only support single instance per class and three classes ('stair', 'curb' and 'doorframe'), 
    and hence, maximum of 3 NPs and 3 BBs
    Example:
                                      doorframe         bb_st           bb_door
                                      v                 vvvvvvvvvvvvvvv vvvvvvvvvvvvvvv
    00000_01_blur1_gaussblur1.png 1 0 1 174 206 170 358 105 105 229 303 100 306 235 363
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^     ^^^^^^^ ^^^^^^^
    filename                      stair np_st   np_door
    [In above example, 'curb' class is not present in the image]
    """
    CLS_IDS     = {'stair' : 0, 'curb' : 1, 'doorframe': 2}
    CLASSES     = ['stair', 'curb', 'doorframe']
    MLC_LBLS    = []

    pngdir    = os.path.dirname(labels_file)
    png       = pngdir.split('/')[-1]
    tgtdir = os.path.join('/'.join(pngdir.split('/')[:-1]), 'Annotations')


    if os.path.exists(tgtdir):
        flist = os.listdir(tgtdir)
        if len(flist) > 0:
            print('Target dir {} is not empty. Aborting!'.format(tgtdir))
            sys.exit(1)
    else:
        os.mkdir(tgtdir)


    f = open(labels_file, 'r')
    for line in f.readlines():
        words = line.strip().split()
        #print 'words: {}'.format(words)
        img = words[0]
        MLC_LBLS = map(bool, map(int, words[1:4]))
        stair, curb, door = MLC_LBLS
        annots = words[4:]
        #print 'img = {},\nstair = {}, curb = {}, door = {} (MLC:{}),\nannots = {}'.format(img, stair, curb, door, MLC_LBLS, annots)
        # Get NPs
        nps = {'stair' : (), 'curb' : (), 'doorframe': () }
        bbs = {'stair' : (), 'curb' : (), 'doorframe': () }
        for i in xrange(len(MLC_LBLS)):
            if MLC_LBLS[i]:
                nps[CLASSES[i]] = annots[0:2]
                annots = annots[2:]
        # Get BBs
        for i in xrange(len(MLC_LBLS)):
            if MLC_LBLS[i]:
                bbs[CLASSES[i]] = annots[0:4]
                annots = annots[4:]
        top = None
        top = Element('annotation')
        addFileName(top, img)
        addSize(top, width, height, 3)
        for lbl in bbs:
            if bbs[lbl]:
                addObject(top, lbl, bbs[lbl])
        #print 'NPs: {},\nBBs: {}'.format(nps, bbs)
        xfile = open(os.path.join(tgtdir, '.'.join(img.split('.')[:-1]))+'.xml', 'w')
        xfile.write(prettify(top))
        xfile.close()

    print 'Created XML annotations in {}'.format(tgtdir)


if len(sys.argv) != 2:
    print 'Error! Provide full path to the labels file as the first argument'
    print 'Usage create_annotations.py <labels_file> [<image_width> <image_height>]'
    sys.exit(1)

srcdir = sys.argv[1]
width  = 300
height = 400
if len(sys.argv) == 4:
    ## override default width and height
    width   = sys.argv[2]
    height  = sys.argv[3]

createAnnotations(srcdir, width, height)


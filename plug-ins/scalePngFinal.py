#! /usr/bin/env python
#
# Scales PNG files in source directories and save to new directories
# Run this on 'augmented' directory to generate 'png' directory with
# final scaled images for CNN training work
############################################################################
#
from gimpfu import *
from gimpenums import *

import sys, os
import pygtk
from glob import glob

pygtk.require("2.0")
import gtk

from scipy.misc import imresize, imread, imsave


# Constants used by the script

#############################################################################
# For GUI directory options.
augDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia/augmented")
#
pngWidth   = 300
pngHeight  = 400

SIG_OK     = -5
SIG_CANCEL = -6
SIG_YES    = -8 
SIG_NO     = -9

def questionBox(msg):
    btype=gtk.MESSAGE_QUESTION
    flag = gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_YES_NO, msg)
    resp = msgBox.run()
    msgBox.destroy()
    return resp

def msgBox(msg, btype=gtk.MESSAGE_INFO):
    flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
    msgBox.run()
    msgBox.destroy()

def scalePngFinal(srcdir, width, height):
    '''
    Registered function; Converts all of the PNGs in the source 'augmented' 
    directory into rescaled PNG files in a target directory. Copies labels too.
    Source type dir name 'augmented' is enforced.
    srcdir: Full path to the 'augmented' directory
    width, height: Output PNG width and height
    '''
    srcAugDir = os.path.realpath(srcdir)
    aug       = srcAugDir.split('/')[-1]
    tgtPngDir = os.path.join('/'.join(srcAugDir.split('/')[:-1]), 'png')

    if aug != 'augmented':
        msgBox("Source type dir ({}) is not named 'augmented'. As a part of the flow, this is a requirement. Aborting!".format(aug), gtk.MESSAGE_ERROR)
        return

    if not os.path.exists(tgtPngDir):
        os.mkdir(tgtPngDir)

    labels_ = os.listdir(srcAugDir)
    labels_.sort()
    filelists = {}
    lfilelists = {}
    labels = []
    # Consider only non-empty directories (useful visual check for the user when these dirs are shown)
    for label in labels_:
        filelist  = glob(os.path.join(srcAugDir, label, '*.png'))
        if len(filelist) == 0:
            continue
        filelist.sort()
        filelists[label] = filelist # store sorted filelist
        labels.append(label)
        lfilelist = glob(os.path.join(srcAugDir, label, 'labels*.txt'))
        lfilelists[label] = lfilelist


    # Each image in non-empty directory in 'augmented/{}', will be rescaled.
    # If the corresponding dir in 'png/{}' dir is non-empty, this script will abort.
    # NOTE: To avoid a certain directory from being considered, temporarily move it out of the 'augmented'
    #       directory before running this script and move back later. This is a workaround for incremental
    #       building of finale PNG image set or in the case of a merged 'augmented' directory.
    for label in labels:
        tgtdir    = os.path.join(tgtPngDir, label)
        if os.path.exists(tgtdir):
            # Make sure that directory is empty. Otherwise quit.
            flist = os.listdir(tgtdir)
            if len(flist) > 0:
                resp = questionBox("Target directory {} is not empty. \n\n\tContinue?".format(tgtdir))
                if not resp == SIG_YES:
                    return
        else:
            os.mkdir(tgtdir)

    # At this point everything is in order. Start the conversion...
    msgBox("Images from following directories will be rescaled: {}".format(labels), gtk.MESSAGE_INFO)

    # Find all of the files in the source directory
    for label in labels:
        tgtdir    = os.path.join(tgtPngDir, label)
        filelist  = filelists[label]
        print "Converting {} directory to PNG.".format(label)
        for srcfile in filelist:
            img    = imread(srcfile, mode='RGB')
            sclimg = imresize(img, (height,width), interp='bicubic')
            imsave(os.path.join(tgtdir, srcfile.split('/')[-1]), sclimg)
        print "{} directory is converted to PNG.".format(label)
        for lfile in lfilelists[label]:
            os.system('cp -f {sl} {dl}'.format(sl=lfile, dl=tgtdir))

    print "The PNG files are successfully created in {}".format(tgtPngDir)

#
############################################################################
#
register (
    "scalePngFinal",           # Name registered in Procedure Browser
    "Rescale images from source 'augmented' directory to output final PNG images in target 'png' directory. Includes relocation of labels.",       # Widget title
    "Rescale images from source 'augmented' directory to output final PNG images in target 'png' directory. Includes relocation of labels.",       # Widget title
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "May 2016",               # Date
    "4. Rescale Augmented Images for Final DB",  # Menu Entry
    "",     # Image Type
    [
    ( PF_DIRNAME, "srcdir", "Input 'augmented' Directory:", augDir ),
    ( PF_INT,     "width",  "Output PNG file width in pixels", pngWidth),
    ( PF_INT,     "height", "Output PNG file heigh in pixels", pngHeight),
    ],
    [],
    scalePngFinal,   # Matches to name of function being defined
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register

main() 

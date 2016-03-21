#! /usr/bin/env python
#
#   File = openImages.py
#   Opens all images from a directory one after another. Allows user
#   to work on one image, save before opening another image.
#
############################################################################
#
from gimpfu import *
from gimpenums import *

import sys, os
from time import sleep
import pickle
import pygtk

pygtk.require("2.0")
import gtk

srcDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia")

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

def msgBox(msg,btype=gtk.MESSAGE_INFO):
    flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
    resp = msgBox.run()
    msgBox.destroy()


def openXcfImages(srcPath):
    """Registered function openImages, opens all XCF images from srcPath
    one at a time. When user closes the image, opens another one to edit.
    """
    ###
    pdb.gimp_displays_flush()
    filelist = os.listdir(srcPath)
    filelist.sort()
    srcfiles = []

    for fname in filelist:
        if not fname.lower().endswith('.xcf'):
            continue # skip non-xcf files
        srcfiles.append(fname)
        srcfile = os.path.join(srcPath, fname)
        img = pdb.gimp_file_load(srcfile, srcfile)
        disp = pdb.gimp_display_new(img)
        sleep(4)
        resp = questionBox('''
Are you ready to work on NEXT IMAGE?

Image will always be saved. Undo changes if you don't want to save them.

Click on 'No' to quit. 
Click on 'Yes' to open next image.''')
        if len(gimp.image_list()) > 0:
            saveImage(img, disp)
        if resp == SIG_NO: # User clicked 'No'
            break

    # Find all of the xcf files in the list
    if len(srcfiles) == 0:
        msgBox("Source directory didn't contain any XCF images.", gtk.MESSAGE_ERROR)
    else:
        msgBox("Done with all images.", gtk.MESSAGE_INFO)

def saveImage(img, disp):
    pdb.gimp_xcf_save(0, img, img.active_drawable, img.filename, img.filename)
    pdb.gimp_image_clean_all(img)
    #pdb.gimp_display_delete(gimp.default_display())
    pdb.gimp_display_delete(disp)
    
#
############################################################################
#
register (
    "openXcfImages",             # Name registered in Procedure Browser
    "Open XCF images from a directory one at a time to edit.", # description
    "Open XCF images from a directory one at a time to edit.", # description
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "2. Open XCF Images",         # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "Source Directory:", srcDir ),
    ],
    [],
    openXcfImages,                 # Matches to name of function being defined
    menu = "<Image>/DVIA/DirectoryLevelOps"  # Menu Location
    )   # End register
#
main() 

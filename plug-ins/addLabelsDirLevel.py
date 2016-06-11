#! /usr/bin/env python
#
#   File = addLayersDirLevel.py
#   Works on all XCF images in a directory for adding labels for DVIA CNN
#
############################################################################
#
from gimpfu import *
import os
import sys
import re
#from time import sleep

import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
from labelCreator import labelCreator

srcDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia")

scriptpath = os.path.dirname(os.path.realpath( __file__ ))

def msgBox(message, type, modal):
    if modal == 0:
        flag = gtk.DIALOG_DESTROY_WITH_PARENT
    else:
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, type, gtk.BUTTONS_OK, message)
    ret = msgBox.run()
    msgBox.destroy()

def addLabelsDirLevel(srcPath):
    """Registered function; selects active image and allows user to add labels for 
    requested classes.
    """
    ###
    pdb.gimp_displays_flush()
    imgs = gimp.image_list()
    if len(imgs) != 0:
        msgBox("Since 'Add Labels' tool works on all images in a directory, please close all open images in Gimp before running it.", gtk.MESSAGE_ERROR, 0)
        return
    labelCreator(srcPath, single=False)

#
############################################################################
#
register (
    "addLabelsDirLevel",      # Name registered in Procedure Browser
    "Add Labels to Multiple Images", # Widget title
    "Add labels to images for CNN classification or detection tasks. Works at direcoty level", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "June 2016",              # Date
    "2b. Add Labels (Dir level)",         # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "Source Directory:", srcDir ),
    ],
    [],
    addLabelsDirLevel,        # Matches to name of function being defined
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register
#
main() 

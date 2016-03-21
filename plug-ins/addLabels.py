#! /usr/bin/env python
#
#   File = addLayers.py
#   Selects active image and adds layers for certain labels for DVIA CNN
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

def addLabels():
    """Registered function; selects active image and allows user to add labels for 
    requested classes.
    """
    ###
    pdb.gimp_displays_flush()
    imgs = gimp.image_list()
    if len(imgs) == 0:
        msgBox("'Add Labels' tool works on an open image. Also make sure to run the 'Set RoI' tool on the image before running this tool.", gtk.MESSAGE_INFO, 0)
        return
    img = imgs[0]

    # If class label exists, prompt user for a bounding box (and nearest point)
    # If not, ask user to choose a label and bounding box (and nearest point)
    pdb.gimp_message("Opening the labelCreator...")
    labelCreator(img)


#
############################################################################
#
register (
    "addLabels",           # Name registered in Procedure Browser
    "Add Classification Labels", # Widget title
    "Add labels for DVIA CNN classification", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "b. Add Labels",          # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ],
    [],
    addLabels,                 # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

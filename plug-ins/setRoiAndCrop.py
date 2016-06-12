#! /usr/bin/env python
#
#   File = setRoiAndCrop.py
#   Acts on user selection to register RoI and crop & resize image.
#
############################################################################
#
from gimpfu import *
import os
from time import sleep
import re
from roiCreator import RoiCreator

import pygtk
pygtk.require('2.0')
import gtk

IMG_SIZE_W = 300
IMG_SIZE_H = 400

srcDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia")

def msgBox(message, typ, modal):
    if modal == 0:
        flag = gtk.DIALOG_DESTROY_WITH_PARENT
    else:
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, typ, gtk.BUTTONS_OK, message)
    msgBox.run()
    msgBox.destroy()

def setRoiAndCrop():
    """Registered function; acts on user selection to register region of interest (RoI)
    and selectively crops around it to save image with new cropped and resized dimensions.
    """
    ###
    pdb.gimp_displays_flush()
    img = gimp.image_list()[0]

    bb = pdb.gimp_selection_bounds(img)   
    if not bb[0]:
        msgBox("Mark a selection for the RoI and call me again.", gtk.MESSAGE_INFO, 0)
        return

    ## Check if the image is XCF. If not, quit with a warning.
    fname = pdb.gimp_image_get_filename(img)
    ext = fname.split('.')[-1].lower()
    if (ext != "xcf"):
        msgBox("You should use this only with XCF images. Make sure to run JPEG/PNG->XCF script on a directory to create directory with XCF images.", gtk.MESSAGE_ERROR, 1)
        return
    roi = RoiCreator(img, IMG_SIZE_W, IMG_SIZE_H, torgb=True)
    roi.doit()

#
############################################################################
#
register (
    "setRoiAndCrop",           # Name registered in Procedure Browser
    "Select RoI and Crop Image", # Widget title
    "Select RoI and Crop Image", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "a. Set RoI",         # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ],
    [],
    setRoiAndCrop,                 # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

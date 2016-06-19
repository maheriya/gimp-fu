#! /usr/bin/env python
#
#   File = addLayers.py
#   Selects active image and adds layers for certain labels for DVIA CNN
#
############################################################################
#
from gimpfu import *
import pygtk
pygtk.require("2.0")
import gtk
from dvia_common import msgBox
from labelCreator import LabelCreator
 
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

    LabelCreator(img)


#
############################################################################
#
register (
    "addLabels",           # Name registered in Procedure Browser
    "Add Labels to a Single Image", # Widget title
    "Add labels to a single image for CNN classification or detection tasks", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "b. Add Labels (Current Image)",          # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ],
    [],
    addLabels,                 # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

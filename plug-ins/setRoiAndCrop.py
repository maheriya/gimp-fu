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

import pygtk
pygtk.require('2.0')
import gtk

IMG_SIZE = 300

srcDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia")

def msgBox(message, type, modal):
    if modal == 0:
        flag = gtk.DIALOG_DESTROY_WITH_PARENT
    else:
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, type, gtk.BUTTONS_OK, message)
    ret = msgBox.run()
    msgBox.destroy()


def processImage(img):
    # This function uses current selection as RoI and tries to center it in the image
    # and crops around it leaving upto 50 pixels on each side or RoI (if possible)

    ## Convert to grayscale and rotate for portrait orientation if required
    if pdb.gimp_image_base_type(img) != 1:  # Not grayscale
        try:
            pdb.gimp_image_convert_grayscale(img)
        except:
            pass

    pdb.gimp_image_resize_to_layers(img)

    # Crop around RoI
    bb  = pdb.gimp_selection_bounds(img)
    roi = pdb.gimp_selection_save(img) #  roi is a channel
    pdb.gimp_item_set_name(roi, "RoI")
    pdb.gimp_item_set_visible(roi, TRUE)
    pdb.gimp_image_select_item(img, 2, roi) # absolute selection
    pdb.gimp_displays_flush()

    # Now grow the selection by 7 percent to cover more around RoI
    roi_w = bb[3]-bb[1]
    roi_h = bb[4]-bb[2]
    roi_x = bb[1]
    roi_y = bb[2]
    # Crop image down. Clamp to smaller of height or width if selection is not square
    if (roi_h < roi_w):
        nw   = roi_h
        nh   = roi_h
    else:
        nw   = roi_w
        nh   = roi_w
    #msgBox("Crop stats: X:{x}, Y:{y}, W:{w}, H:{h}".format(x=roi_x, y=roi_y, w=nw, h=nh), gtk.MESSAGE_INFO, 0)
    pdb.gimp_image_resize(img, nw, nh, -roi_x, -roi_y)

    # Now scale the image down to have max of 480 dimension (images smaller than this are left untouched)
    if nw > IMG_SIZE:
        nw = IMG_SIZE
        nh = IMG_SIZE
    pdb.gimp_image_scale(img, nw, nh)
    pdb.gimp_selection_none(img)
    try:
        pdb.gimp_image_set_active_layer(img, pdb.gimp_image_get_layer_by_name(img, 'group'))
    except:
        pass


def setRoiAndCrop():
    """Registered function; acts on user selection to register region of interest (RoI)
    and selectively crops around it to save image with new cropped and resized dimensions.
    """
    ###
    pdb.gimp_displays_flush()
    img = gimp.image_list()[0]

    bb = pdb.gimp_selection_bounds(img)   
    if not bb[0]:
        msgBox("Make a SQUARE selection for the RoI and call me again.", gtk.MESSAGE_INFO, 0)
        return

    ## Check is the image is XCF. If not, quit with a warning.
    fname = pdb.gimp_image_get_filename(img)
    ext = fname.split('.')[-1].lower()
    if (ext != "xcf"):
        msgBox("You should use this only with XCF images. Make sure to run JPEG/PNG->XCF script on a directory to create directory with XCF images.", gtk.MESSAGE_ERROR, 1)
        return
    processImage(img)
    #drw = img.active_drawable
    #tgtFile = pdb.gimp_image_get_filename(img)
    #pdb.gimp_xcf_save(0, img, drw, tgtFile, tgtFile)
    #pdb.gimp_image_clean_all(img)
    #pdb.gimp_display_delete(gimp.default_display())

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

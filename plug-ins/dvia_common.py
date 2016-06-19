#   File = dvia_common.py
#   Several common definitions
#
############################################################################
from gimpfu import *
import pygtk
pygtk.require("2.0")
import gtk

import os
#import pickle
#from pprint import pprint

if os.name == 'posix':
    HOME = os.environ['HOME']
elif os.name == 'nt':
    HOME = os.environ['HOMEPATH']


## Empty definitions for labels, layers and NP/BB
dvia_classes      = ('catchall', 'stair', 'curb', 'doorframe')
dvia_cls_ids      = {'stair' : 0, 'curb' : 1, 'doorframe': 2}  ## catchall should be ignored -- this should only be used for MLC format

dvia_bordercolors = {'catchall': '#ffffff', 'stair': '#b80c48', 'curb': '#09b853', 'doorframe': '#0c84b8'}
dvia_labels       = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False} #, 'badfloor': False, 'drop': False }
dvia_layers       = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False} #, 'badfloor': False, 'drop': False }

# Objects: Per class array of objects which are dict of arrays or nps and bbs
dvia_objects = {'catchall' : [], 'stair' : [], 'curb' : [], 'doorframe': []}
# Object: Each object contains one np, and one bb. Also used to store other object specific info.
dvia_object  = {'np': (), 'bb': (), 'npLayer': None, 'bbLayer': None, 'index': None} ##, 'pose': 'front'}

dvia_ldata =  {'labels': dvia_labels, 'layers': dvia_layers, 'objects': dvia_objects}




## Common function definitions
def msgBox(message, typ=gtk.MESSAGE_INFO, modal=1):
    if modal == 0:
        flag = gtk.DIALOG_DESTROY_WITH_PARENT
    else:
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    mBox = gtk.MessageDialog(None, flag, typ, gtk.BUTTONS_OK, message)
    mBox.run()
    mBox.destroy()

def questionBox(msg):
    btype=gtk.MESSAGE_QUESTION
    flag = gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_YES_NO, msg)
    resp = msgBox.run()
    msgBox.destroy()
    return resp


def createBBVisual(img, lyr, lbl, make_border=True):
    # Based on input bb, creates a color-coded bounding box visual in the img for label lbl
    # Return newly calculated bounding box based on new box (this avoids out of bound selections)

    # Create a solid gray box: required to make sure some part of BB remains visible during augmentation
    pdb.gimp_context_set_background('#606060')
    pdb.gimp_edit_bucket_fill(lyr, BG_BUCKET_FILL, NORMAL_MODE, 50, 0, FALSE, 0, 0)
    
    # Optionally create a border
    if make_border:
        # Add border
        pdb.gimp_selection_shrink(img, 1)
        pdb.gimp_selection_border(img, 1)
        pdb.gimp_selection_grow(img, 1)
        gimp.set_foreground(dvia_bordercolors[lbl])
        pdb.gimp_edit_bucket_fill(lyr, FG_BUCKET_FILL, NORMAL_MODE, 70, 0, FALSE, 0, 0)

    pdb.gimp_image_select_item(img, CHANNEL_OP_REPLACE, lyr)
    # Get new bounding box
    bb = pdb.gimp_selection_bounds(img)
    pdb.gimp_selection_none(img)
    pdb.gimp_displays_flush()
    return tuple(bb[1:])

def createNPVisual(img, lyr, lbl, make_gradient=True):
    x1,y1, x2,y2 = pdb.gimp_selection_bounds(img)[1:]
    xc = x1 + (x2-x1)/2
    # Create a circle selection
    pdb.gimp_image_select_ellipse(img, CHANNEL_OP_REPLACE, xc-5, y2-11, 11, 11)

    # Select again for accuracy
    x1,y1, x2,y2 = pdb.gimp_selection_bounds(img)[1:]
    # Find the bottom-center of the bounding box
    xc = x1 + (x2-x1)/2
    yc = y1 + (y2-y1)/2
    gimp.set_background('#ffffff')
    if make_gradient:
        ## Gradient fill to create a distinct cone:
        gimp.set_foreground(dvia_bordercolors[lbl])
        pdb.gimp_context_set_gradient('FG to BG (RGB)') # 'Caribbean Blues'
        pdb.gimp_edit_blend(lyr, CUSTOM_MODE, NORMAL_MODE, GRADIENT_CONICAL_SYMMETRIC, 
                            100, 1, REPEAT_NONE, FALSE, FALSE, 1, 0.0, FALSE, xc,yc,xc,y2)
    else:
        ## Simple flat bucket fill
        pdb.gimp_edit_bucket_fill(lyr, BG_BUCKET_FILL, NORMAL_MODE, 100, 0, FALSE, 0, 0)

    pdb.gimp_selection_none(img)
    pdb.gimp_displays_flush()
    return (xc, y2)

#EOF
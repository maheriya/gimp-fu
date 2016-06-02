#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
from gimpenums import *
import os
import re
import pickle
#
import pygtk
pygtk.require('2.0')
import gtk
#

def msgBox(message, type, modal):
    if modal == 0:
        flag = gtk.DIALOG_DESTROY_WITH_PARENT
    else:
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, type, gtk.BUTTONS_OK, message)
    ret = msgBox.run()
    msgBox.destroy()


if os.name == 'posix':
    Home = os.environ['HOME']
elif os.name == 'nt':
    Home = os.environ['HOMEPATH']
xcfDir = os.path.join(Home, "Projects/IMAGES/dvia")
jpegDir = os.path.join(Home, "Projects/IMAGES/dvia")


def processImage(img):

    ## Convert to RGB if required
    if pdb.gimp_image_base_type(img) != 0:  # Not RGB
        try:
            pdb.gimp_image_convert_rgb(img)
        except:
            pass

    pdb.gimp_image_resize_to_layers(img)

    ASPECT = None
    ## Crop if required for aspect ratio
    if ASPECT == "640/480":
        aspectRatio = 1.0 * img.height / img.width
        desiredAspect = 640.0 / 480.0
        height = img.height
        width  = img.width
        if (aspectRatio > (desiredAspect + 0.005)):
            # # Too tall. Need to crop
            height = round(1.0 * img.width * 640 / 480)
            width  = img.width 
        elif (aspectRatio < (desiredAspect - 0.005)):
            # # Too wide. Need to crop.
            height = img.height
            width  = round(1.0 * img.height * 480 / 640)
    elif ASPECT == "400x400":
        ## For square images, calculation is much straightforward
        ## We simply take the min dimension as width and height
        height = min(img.height, img.width)
        width  = height

    if ASPECT is not None:
        ## We retain bottom-left corner, cropping top or right edge as required
        pdb.gimp_image_crop(img, width, height, img.width-width, img.height-height)


def saveJpgToXcf(srcPath, tgtPath):
    """Registered function; Converts all of the jpeg/png images in the source
    directory into xcf files in a target directory. Requires two arguments, 
    the paths to the source and target directories. DOES NOT require an open image.
    """
    ###
    pdb.gimp_displays_flush()
    open_images, image_ids = pdb.gimp_image_list()
    if open_images > 0:
        pdb.gimp_message ("Close open Images & Rerun")
        return

    propList = [('default', 'default')]
    propList.append(('Grouped', 'True'))
    allFileList = os.listdir(srcPath)
    srcFileList = []
    tgtFileList = []
    # Find all of the jpeg or png files in the list & make xcf file names
    if len(allFileList) == 0:
        msgBox("Didn't find any files in the directory {}.".format(srcPath), gtk.MESSAGE_INFO, 1)
        return

    label = srcPath.split(os.path.sep)[-1:][0]
    #msgBox("d: {}\nLabel: {}".format(srcPath, label), gtk.MESSAGE_INFO, 1)

    lbls = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False, 'badfloor': False, 'drop': False }
    lyrs = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False, 'badfloor': False, 'drop': False }
    ldata = {'labels': lbls, 'layers': lyrs}

    # Write label parasite
    lbl = None
    if not label.startswith('multi'):
        ## Not a multiclass image
        lbl = '_'.join(label.split('_')[1:])
        lbls[lbl] = True

    imgid = 0
    for fname in allFileList:
        (r, ext) = os.path.splitext(fname.lower())
        if ext == '.jpg' or ext == '.jpeg' or ext == '.png':
            srcFileList.append(fname)
            #tgtFileList.append("{l}_{n:0>5}.xcf".format(l=label, n=imgid))
            # Not needed for object detection
            tgtFileList.append("{n:0>5}.xcf".format(n=imgid))
            imgid += 1

    # Dictionary - source & target file names
    tgtFileDict = dict(zip(srcFileList, tgtFileList))
    # Loop on jpegs, open each & save as xcf
    for srcFile in srcFileList:
        tgtFile = os.path.join(tgtPath, tgtFileDict[srcFile])
        srcFile = os.path.join(srcPath, srcFile)
        if srcFile.count('.png') > 0: # PNG file
            img = pdb.file_png_load(srcFile, srcFile)
        else: # JPEG file
            img = pdb.file_jpeg_load(srcFile, srcFile)

        base = pdb.gimp_image_get_active_layer(img)
        base.name = 'base'
        ## Create a group
        grp = pdb.gimp_layer_group_new(img)
        grp.name = 'group'
        pdb.gimp_image_insert_layer(img, grp, None, -1) # Insert group into image
        pdb.gimp_image_reorder_item(img, base, grp, -1) # Move base layer into 'grp' group

        processImage(img)

        img.attach_new_parasite('ldata', 5, pickle.dumps(ldata))
        drw = img.active_drawable
        # Set Flag Properties / Parasites
        pdb.gimp_xcf_save(0, img, drw, tgtFile, tgtFile)
        pdb.gimp_image_delete(img)
        #msgBox("Done with {s}->{t}".format(s=srcFile, t=tgtFile), gtk.MESSAGE_INFO, 1)

#
############################################################################
#
register (
    "saveJpgToXcf",           # Name registered in Procedure Browser
    "Convert JPG/PNG files to XCF", # Widget title
    "Convert JPG/PNG files to XCF", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "1. Convert JPG/PNG to XCF", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "JPG Originals (source) Directory:", jpegDir ),
    ( PF_DIRNAME, "tgtPath", "XCF Working (target) Directory:", xcfDir ),
    ],
    [],
    saveJpgToXcf,      # Matches to name of function being defined
    menu = "<Image>/DVIA/DirectoryLevelOps"   # Menu Location
    )   # End register
#
main() 

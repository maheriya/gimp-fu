#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
from gimpenums import *
import pygtk
pygtk.require('2.0')
import gtk
import os
import pickle
import dvia_common as dv

IMG_SMALLER_EDGE_SIZE_MAX = 1200.0  # Clamp smaller edge of the image to this size 

xcfDir = os.path.join(dv.HOME, "Projects/IMAGES/dvia")
jpegDir = os.path.join(dv.HOME, "Projects/IMAGES/dvia")


def processImage(img):
    ## Convert to RGB if required
    if pdb.gimp_image_base_type(img) != 0:  # Not RGB
        try: pdb.gimp_image_convert_rgb(img)
        except: pass

    pdb.gimp_image_resize_to_layers(img)
    smin = min(img.height, img.width)
    # Clamp smaller edge to 1500
    if smin > IMG_SMALLER_EDGE_SIZE_MAX:
        sscale = float(IMG_SMALLER_EDGE_SIZE_MAX / smin)
        height = round(img.height*sscale)
        width  = round(img.width*sscale)
        pdb.gimp_context_set_interpolation(INTERPOLATION_LANCZOS)
        pdb.gimp_image_scale(img, width, height)


def saveJpgToXcf(srcPath, tgtPath):
    """Registered function; Converts all of the jpeg/png/gif images in the source
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
        dv.msgBox("Didn't find any files in the directory {}.".format(srcPath), gtk.MESSAGE_INFO, 1)
        return

    label = srcPath.split(os.path.sep)[-1:][0]

    lbls = dv.dvia_labels
    ldata = dv.dvia_ldata

    # Write label parasite
    lbl = None
    if not label.startswith('multi'):
        ## Not a multiclass image
        lbl = '_'.join(label.split('_')[1:])
        lbls[lbl] = True

    imgid = 0
    for fname in allFileList:
        (r, ext) = os.path.splitext(fname.lower())
        if ext == '.jpg' or ext == '.jpeg' or ext == '.png' or ext == '.gif':
            srcFileList.append(fname)
            tgtFileList.append("{l}_{n:0>5}.xcf".format(l=label, n=imgid))
            imgid += 1

    # Dictionary - source & target file names
    tgtFileDict = dict(zip(srcFileList, tgtFileList))
    # Loop on jpegs, open each & save as xcf
    for srcFile in srcFileList:
        tgtFile = os.path.join(tgtPath, tgtFileDict[srcFile])
        srcFile = os.path.join(srcPath, srcFile)
        if srcFile.count('.png') > 0: # PNG file
            img = pdb.file_png_load(srcFile, srcFile)
        if srcFile.count('.gif') > 0: # GIF file
            img = pdb.file_gif_load(srcFile, srcFile)
        else: # JPEG file
            img = pdb.file_jpeg_load(srcFile, srcFile)

        processImage(img)

        base = pdb.gimp_image_get_active_layer(img)
        base.name = 'base'
        ## Create a group
        grp = pdb.gimp_layer_group_new(img)
        grp.name = 'group'
        pdb.gimp_image_insert_layer(img, grp, None, -1) # Insert group into image
        pdb.gimp_image_reorder_item(img, base, grp, -1) # Move base layer into 'grp' group


        img.attach_new_parasite('ldata', 5, pickle.dumps(ldata))
        drw = img.active_drawable
        # Set Flag Properties / Parasites
        pdb.gimp_xcf_save(0, img, drw, tgtFile, tgtFile)
        #dv.msgBox("Done with {s}->{t}".format(s=srcFile, t=tgtFile), gtk.MESSAGE_INFO, 1)
        pdb.gimp_image_delete(img)

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
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register
#
main() 

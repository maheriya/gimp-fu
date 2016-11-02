#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
from gimpenums import *
import pygtk
from IN import PF_FILE
pygtk.require('2.0')
import gtk
import os, sys
import pickle
import dvia_common as dv

def regenerateXcfFromOriginal(srcDir):
    """
    Replaces the currently open XCF image by the original JPG/PNG image it was converted from.
    User supplies directory path of the original directory.
    """
    ###
    pdb.gimp_displays_flush()
    open_images = pdb.gimp_image_list()[0]
    if open_images != 1:
        dv.msgBox("This routine works on a single open image. Try again!", gtk.MESSAGE_ERROR)
        return
    ## Look for DB file and exit if not found
    img = gimp.image_list()[0]
    tgtPath = os.path.dirname(img.filename)
    tgtFile = os.path.basename(img.filename)
    dbfilename = os.path.join(tgtPath, dv.DBFILENAME)
    if not os.path.exists(dbfilename):
        dv.msgBox("Couldn't open DB file {}. Can't find original directory without that.".format(dv.DBFILENAME), gtk.MESSAGE_ERROR)
        return

    with open(dbfilename, 'r') as f:
        flagsdb = pickle.load(f)
        f.close()
    if not 'xcf2orig' in flagsdb:
        dv.msgBox("Couldn't do reverse look up in the DB {}. Can't find original directory without that.".format(dv.DBFILENAME), gtk.MESSAGE_ERROR)
        return
    srcPath = srcDir
    srcFile = flagsdb['xcf2orig'][tgtFile]


    propList = [('default', 'default')]
    propList.append(('Grouped', 'True'))
    label = srcPath.split(os.path.sep)[-1:][0]

    ldata = dv.dvia_ldata

    # Write label parasite
    lbl = None
    if not label.startswith('multi'):
        ## Not a multiclass image
        lbl = '_'.join(label.split('_')[1:])
        ldata['labels'][lbl] = True
        print("Added label {} to {}".format(lbl, tgtFile))
    dv.convertToXcf(srcPath, srcFile, tgtPath, tgtFile, ldata)
    # It is better to delete the old display so that user is forced to reopen the image (next or prev if using
    # Without this, the user may end up re-editing the old image
    pdb.gimp_display_delete(gimp.default_display())   

#
############################################################################
#
jpegDir = os.path.join(dv.HOME, "Projects/IMAGES/dvia")
register (
    "regenerateXcfFromOriginal",                    # Name registered in Procedure Browser
    "Regenerate Current XCF from Original JPG/PNG", # Widget title
    "Regenerate Current XCF from original JPG/PNG by doing a reverse look up", #
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "July 2016",              # Date
    "d. Regenerate Current XCF from Original JPG/PNG", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcDir", "JPG/PNG Source Directory:", jpegDir ),
    ],
    [],
    regenerateXcfFromOriginal,      # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

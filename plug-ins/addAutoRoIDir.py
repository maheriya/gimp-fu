#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
from gimpenums import *
import pygtk
pygtk.require('2.0')
import gtk
import os, sys
import pickle
import dvia_common as dv
from roiCreator import RoiCreator

ONLY_UPDATE_DB = True # Hack to update DB file of an existing XCF directory without modifying XCF files

def addAutoRoIDir(srcDir):
    """Registered function; Adds RoI to all XCF images in a directory and
    updates the DB. RoI is assumed to be the full image.
    Once this routine is done, 'Dir Ops (Det)' -> '2b. Add RoI and Labels' menu should be used to review
    all images and re-do RoI for images that need specific RoI. In order to do that, use the 
    'd. Regenerate Current XCF from Original JPG/PNG' menu to first get XCF re-generated from original,
    and then adding RoI manually as usual.
    """
    pdb.gimp_displays_flush()
    open_images = pdb.gimp_image_list()[0]
    if open_images > 0:
        dv.msgBox("Close all open images and try again!", gtk.MESSAGE_ERROR)
        return

    dbfilename = os.path.join(srcDir, dv.DBFILENAME)
    if not os.path.exists(dbfilename):
        dv.msgBox("Couldn't open DB file {}. Refusing to go further!".format(dv.DBFILENAME), gtk.MESSAGE_ERROR)
        return

    with open(dbfilename, 'r') as f:
        flagsdb = pickle.load(f)
        f.close()


    ## Bootstrap DB with ROI and other info
    if not 'ROI' in flagsdb:
        flagsdb['ROI']   = {}  # For each image, True: RoI exists; False: RoI doesn't exist
        flagsdb['LDATA'] = {}  # For each image, ldata (dvia_ldata format)
        flagsdb['currFile']      = None       # current working image file name
        flagsdb['indexFilename'] = 0      # current index based on Filename sort.
        flagsdb['indexRoI']      = 0      # current index based on RoI sort.
        flagsdb['currSort']      = 'Filename'

    srcfiles = []
    for fname in os.listdir(srcDir):
        if not fname.lower().endswith('.xcf'):
            continue # skip non-xcf files
        srcfiles.append(fname)
    if len(srcfiles) == 0:
        dv.msgBox("Source directory {} didn't contain any XCF images.".format(srcDir), gtk.MESSAGE_ERROR)
        return

    for srcfile in srcfiles:
        srcfullpath = os.path.join(srcDir, srcfile)
        img  = pdb.gimp_file_load(srcfullpath, srcfullpath)
        #disp = pdb.gimp_display_new(self.img)

        # Check image for label data.
        para = img.parasite_find('ldata')
        if para:
            ldata = pickle.loads(para.data)
        else:
            ldata  = dict(dv.dvia_ldata)

        ## Update DB
        flagsdb['LDATA'][srcfile] = dict(ldata)

        ch = pdb.gimp_image_get_channel_by_name(img, 'RoI')
        if ch is None: # RoI doesn't exist
            ## Whole image to be selected as RoI
            print("{}: Adding RoI".format(srcfile))
            pdb.gimp_selection_all(img)
            roi = RoiCreator(img, dv.IMG_SIZE_MIN, dv.IMG_SIZE_MAX, torgb=True)
            roi.doit()
            flagsdb['ROI'][srcfile] = True
        else:
            print("{}: RoI exists".format(srcfile))

        #save parasite
        try: img.attach_new_parasite('ldata', 5, pickle.dumps(ldata))
        except:
            pdb.gimp_message("Could not save ldata parasite for {}".format(srcfile))

        pdb.gimp_xcf_save(0, img, img.active_drawable, srcfullpath, srcfullpath)
        pdb.gimp_image_delete(img)


    ## saveDB
    try: dbfile = open(dbfilename, 'w')
    except:
        print('Could not open DB file {}'.format(dbfilename))
        dv.msgBox('Could not open DB file {}'.format(dbfilename), gtk.MESSAGE_ERROR)
        raise
    pickle.dump(flagsdb, dbfile)
    dbfile.close()


#
############################################################################
#
xcfDir = os.path.join(dv.HOME,  "Projects/IMAGES/dvia")
register (
    "addAutoRoIDir",           # Name registered in Procedure Browser
    "Add RoI Automatically",   # Widget title
    "Automatically add RoI to all images -- RoI will be full image area", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "July 2016",              # Date
    "5. Add RoI Automatically", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcDir", "XCF Directory:",     xcfDir ),
    ],
    [],
    addAutoRoIDir,      # Matches to name of function being defined
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register
#
main() 

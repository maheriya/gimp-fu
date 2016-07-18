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

def saveJpgToXcfSingle(srcImageFilePath, tgtPath, tgtFileIndex):
    """
    Registered function; Converts a single jpeg/png/gif image directory into xcf file
    in the target directory. Uses common DB for updating the target directory.
    """
    ###
    srcPath = os.path.dirname(srcImageFilePath)
    srcFile = os.path.basename(srcImageFilePath)
    ## Look for DB file and use it to bootstrap if it exists
    dbfilename = os.path.join(tgtPath, dv.DBFILENAME)
    flagsdb = {}

    if os.path.exists(dbfilename):
        with open(dbfilename, 'r') as f:
            flagsdb = pickle.load(f)
        f.close()
    if not 'orig2xcf' in flagsdb:
        flagsdb['orig2xcf'] = {}  # For orig -> xcf  look up
        flagsdb['xcf2orig'] = {}  # For xcf  -> orig  reverse look up
        flagsdb['last'] = -1

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

    pdb.gimp_displays_flush()
    open_images = pdb.gimp_image_list()[0]
    if open_images > 0:
        pdb.gimp_message ("Close open Images & Rerun")
        return

    ext = os.path.splitext(srcFile.lower())[1]
    if ext == '.jpg' or ext == '.jpeg' or ext == '.png' or ext == '.gif':
        if srcFile in flagsdb['orig2xcf']:
            # This file already exists in db
            print("File {} exists".format(srcFile))
            xcfname = flagsdb['orig2xcf'][srcFile] # Override XCF file name since it already exists
        else:
            if tgtFileIndex > flagsdb['last']: 
                flagsdb['last'] = tgtFileIndex
            xcfname = "{l}_{n:0>5}.xcf".format(l=label, n=tgtFileIndex)
            flagsdb['orig2xcf'][srcFile] = xcfname
            flagsdb['xcf2orig'][xcfname] = srcFile 
            print("Added new {}".format(fname))
    else:
        dv.msgBox('Only images of type jpg, png and gif are supported', gtk.MESSAGE_ERROR)
        return

    dv.convertToXcf(srcPath, srcFile, tgtPath, xcfname, ldata)

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
jpegDir = os.path.join(dv.HOME, "Projects/IMAGES/dvia")
register (
    "saveJpgToXcfSingle",           # Name registered in Procedure Browser
    "Convert a single JPG/PNG file to XCF", # Widget title
    "Convert a single JPG/PNG file to XCF", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "July 2016",              # Date
    "a. Convert JPG/PNG to XCF", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_FILENAME,    "srcImageFilePath", "JPG/PNG Source Image:", jpegDir ),
    ( PF_DIRNAME, "tgtPath",          "XCF Target Directory:", xcfDir ),
    ( PF_INT,     "tgtFileIndex",     "XCF output file name index (optional if XCF for source image exists):", 10),
    ],
    [],
    saveJpgToXcfSingle,      # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

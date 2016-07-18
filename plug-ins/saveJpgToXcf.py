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

ONLY_UPDATE_DB = True # Hack to update DB file of an existing XCF directory without modifying XCF files

def saveJpgToXcf(srcPath, tgtPath, convPref):
    """Registered function; Converts all of the jpeg/png/gif images in the source
    directory into xcf files in a target directory. Requires two arguments, 
    the paths to the source and target directories. DOES NOT require an open image.
    The original file names are stored in DBFILENAME file as pickle
    """
    ###
    ## Look for DB file and use it to bootstrap if it exists
    dbfilename = os.path.join(tgtPath, dv.DBFILENAME)
    flagsdb = {}
    if ONLY_UPDATE_DB:
        pass
    else:
        if (convPref == 'scratch'): # Create everything in XCF directory from scratch
            os.system('rm -f {}/*'.format(tgtPath))
            os.system('rm -f {}'.format(dbfilename))

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

    allFileList = os.listdir(srcPath)
    srcFileList = []
    tgtFileList = []
    # Find all of the jpeg or png files in the list & make xcf file names
    if len(allFileList) == 0:
        dv.msgBox("Didn't find any files in the directory {}.".format(srcPath), gtk.MESSAGE_INFO, 1)
        return

    for fname in allFileList:
        ext = os.path.splitext(fname.lower())[1]
        if ext == '.jpg' or ext == '.jpeg' or ext == '.png' or ext == '.gif':
            if fname in flagsdb['orig2xcf']:
                # This file already exists in db
                print("File {} exists".format(fname))
                if (convPref == 'incr') or (convPref == 'update'): # keep existing
                    continue
            else: # New file (same when in 'scratch' mode as db would have been deleted earlier)
                flagsdb['last'] += 1
                xcfname = "{l}_{n:0>5}.xcf".format(l=label, n=flagsdb['last'])
                flagsdb['orig2xcf'][fname]   = xcfname
                flagsdb['xcf2orig'][xcfname] = fname 
                srcFileList.append(fname)
                tgtFileList.append(xcfname)
                print("Added new {}".format(fname))
    # Now go through flagsdb to check if there are files that need to be deleted for convPref == 'update'
    if ONLY_UPDATE_DB:
        pass
    else:
        if convPref == 'update':
            fnames = [f for f in flagsdb['orig2xcf']]
            for fname in fnames:
                if not fname in allFileList:
                    xcfname = flagsdb['orig2xcf'][fname]
                    os.system('rm -f {}'.format(os.path.join(tgtPath, xcfname)))
                    del(flagsdb['xcf2orig'][xcfname])
                    del(flagsdb['orig2xcf'][fname])
                    print("Deleted {} ({})".format(xcfname, fname))
        # Dictionary - source & target file names
        tgtFileDict = dict(zip(srcFileList, tgtFileList))
        # Loop on jpegs, open each & save as xcf
        for srcFile in srcFileList:
            tgtFileName = tgtFileDict[srcFile]
            dv.convertToXcf(srcPath, srcFile, tgtPath, tgtFileName, ldata)

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
    "saveJpgToXcf",           # Name registered in Procedure Browser
    "Convert JPG/PNG files to XCF", # Widget title
    "Convert JPG/PNG files to XCF", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "1. Convert JPG/PNG to XCF", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "JPG/PNG Source Directory:", jpegDir ),
    ( PF_DIRNAME, "tgtPath", "XCF Target Directory:",     xcfDir ),
    ( PF_RADIO,   "convPref", "Preference for conversion:", "incr", (("Incremental: Add new; keep existing; nothing deleted",       "incr"), 
                                                                     ("Update: Add new; keep existing; delete files not in Source", "update"),
                                                                     ("Scratch: Convert all images from scratch",                   "scratch"))),
    ],
    [],
    saveJpgToXcf,      # Matches to name of function being defined
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register
#
main() 

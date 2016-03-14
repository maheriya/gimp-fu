#! /usr/bin/env python
#
#   File = openImages.py
#   Opens all images from a directory one after another. Allows user
#   to work on one image, save before opening another image.
#
############################################################################
#
from gimpfu import *
import os
from time import sleep
import re

if os.name == 'posix':
    Home = os.environ['HOME']
elif os.name == 'nt':
    Home = os.environ['HOMEPATH']

srcDir = os.path.join(Home, "Projects/IMAGES/dvia")

def openImages(srcPath):
    """Registered function openImages, opens all (or XCF?) images from srcPath
    one at a time. When user closes the image, opens another one to edit.
    """
    ###
    pdb.gimp_displays_flush()
    allFileList = os.listdir(srcPath)
    srcFileList = []
    # Find all of the XCF files in the list
    for fname in allFileList:
        srcFileList.append(fname)

    # Open image one at a time
    for srcFile in srcFileList:
        srcFile = os.path.join(srcPath, srcFile)
        img = pdb.gimp_file_load(srcFile, srcFile)
        pdb.gimp_display_new(img)
        while len(gimp.image_list()) > 0:
            sleep(1);

#
############################################################################
#
register (
    "openImages",             # Name registered in Procedure Browser
    "Open Images One at a Time", # Widget title
    "Open Images in a Sequence to Edit and Save", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "2. Open Images from a Directory",         # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "Source) Directory:", srcDir ),
    ],
    [],
    openImages,                 # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register
#
main() 

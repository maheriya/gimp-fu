#! /usr/bin/env python
#
#   File = openImages.py
#   Opens all images from a directory one after another. Allows user
#   to work on one image, save before opening another image.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

srcDir = os.path.join(Home, "Projects/IMAGES/dvia_images")

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
        #fnameLow = fname.lower()
        #if fnameLow.count('.xcf') > 0:  ## open only XCF images
        #    srcFileList.append(fname)
        srcFileList.append(fname)
    # Loop on jpegs, open each & save as xcf
    for srcFile in srcFileList:
        srcFile = os.path.join(srcPath, srcFile)
        img = pdb.gimp_file_load(srcFile, srcFile)
        pdb.gimp_display_new(img)
        while len(gimp.image_list()) > 0:
            sleep(2);

#
############################################################################
#
register (
    "python_fu_openImages",           # Name registered in Procedure Browser
    "Open Images One at a Time", # Widget title
    "Open Images in a Sequence to Edit and Save", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "Open Images from a Directory",         # Menu Entry
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

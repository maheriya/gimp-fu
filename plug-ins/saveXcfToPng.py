#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
import os
import re
#
if os.name == 'posix':
    Home = os.environ['HOME']
elif os.name == 'nt':
    Home = os.environ['HOMEPATH']
xcfDir = os.path.join(Home, "Projects/IMAGES/dvia")
pngDir = os.path.join(Home, "Projects/IMAGES/dvia")
#

def saveXcfToPng(srcPath, tgtPath):
    """Registered function; Converts all of the Xcfs in the source directory
    into PNG files in a target directory.  Requires two arguments, the paths
    to the source and target directories.  DOES NOT require an image to be open.
    """
    # Find all of the files in the source and target directories
    allFileList = os.listdir(srcPath)
    srcFileList = []
    tgtFileList = []
    # Index for parasites
    xform = re.compile('\.xcf', re.IGNORECASE)
    # Find all of the xcf files in the list & make png file names
    for fname in allFileList:
        fnameLow = fname.lower()
        if fnameLow.count('.xcf') > 0:
            srcFileList.append(fname)
            tgtFileList.append(xform.sub('.png',fname))
    tgtFileDict = dict(zip(srcFileList, tgtFileList))
    for srcFile in srcFileList:
        srcFilePath = os.path.join(srcPath, srcFile)
        theImage = pdb.gimp_file_load(srcFilePath, srcFilePath)
        pdb.gimp_image_scale(theImage, 28, 28)
        theDrawable = theImage.active_drawable
        tgtFilePath = os.path.join(tgtPath, tgtFileDict[srcFile])
        # All sorts of parameters on PNG save
        theDrawable = pdb.gimp_image_flatten(theImage)
        #pdb.file_jpeg_save(theImage, theDrawable, tgtFilePath, tgtFilePath, quality, 0, 1, 0, "", 0, 1, 0, 0)
        compression = 0; # 9
        pdb.file_png_save(theImage, theDrawable, tgtFilePath, tgtFilePath, 0, compression, 0, 0, 0, 0, 0)
        pdb.gimp_image_delete(theImage)
#
############################################################################
#
register (
    "saveXcfToPng",           # Name registered in Procedure Browser
    "XCF to PNG",             # Widget title
    "Convert XCF to PNG",     #
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "5. Convert XCF to PNG (Directory)", # Menu Entry
    "",     # Image Type
    [
    ( PF_DIRNAME, "srcPath", "XCF Images (source) Directory:", xcfDir ),
    ( PF_DIRNAME, "tgtPath", "PNG Images (target) Directory:", pngDir ),
    ],
    [],
    saveXcfToPng,   # Matches to name of function being defined
    menu = "<Image>/DVIA"  # Menu Location
    )   # End register

main() 

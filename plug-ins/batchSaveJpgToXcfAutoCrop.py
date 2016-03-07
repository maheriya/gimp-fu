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
xcfDir = os.path.join(Home, "Projects/IMAGES/dvia_images")
jpegDir = os.path.join(Home, "Projects/IMAGES/dvia_images")

def PropWrite(theImage, pList):
    pIndex = 5
    for (pName, pVal) in pList:
        theImage.attach_new_parasite(pName, pIndex, pVal)

def processImage(img):
    ## Convert to grayscale and rotate for portrait orientation if required
    if pdb.gimp_image_base_type(img) != 1:  # Not grayscale
        try:
            pdb.gimp_image_convert_grayscale(img)
        except:
            pass
    
    if (img.width > img.height): # landscape aspect ratio -> rotate CCW90
        pdb.gimp_image_rotate(img, 2)
    
    pdb.gimp_image_resize_to_layers(img)
    
    ## Crop if required for aspect ratio
    aspectRatio = 1.0 * img.height / img.width
    desiredAspect = 640.0/480.0
    newH = img.height
    newW = img.width
    if (aspectRatio > (desiredAspect + 0.005)):
        ## Too tall. Need to crop
        newH = round(1.0 * img.width * 640 / 480)
        newW = img.width 
    elif (aspectRatio < (desiredAspect - 0.005)):
        ## Too wide. Need to crop.
        newH = img.height
        newW = round(1.0 * img.height * 480 / 640)
    
    newAspect = 1.0 * newH / newW
    pdb.gimp_image_crop(img, newW, newH, 0, img.height-newH)


def batchSaveJpgToXcfAutoCrop(srcPath, tgtPath):
    """Registered function autoJpgToXcf, Converts all of the
    jpegs in the source directory into xcf files in a target 
    directory.  Requires two arguments, the paths to the source and
    target directories.  DOES NOT require an image to be open.
    """
    ###
    pdb.gimp_displays_flush()
    open_images, image_ids = pdb.gimp_image_list()
    if open_images > 0:
        pdb.gimp_message ("Close open Images & Rerun")
    else:
        propList = [('default', 'default')]
        propList.append(('Class', 'Stair'))
        allFileList = os.listdir(srcPath)
        existingList = os.listdir(tgtPath)
        srcFileList = []
        tgtFileList = []
        xform = re.compile('\.jpg', re.IGNORECASE)
        # Find all of the jpeg files in the list & make xcf file names
        for fname in allFileList:
            fnameLow = fname.lower()
            if fnameLow.count('.jpg') > 0:
                srcFileList.append(fname)
                tgtFileList.append(xform.sub('.xcf',fname))
        # Dictionary - source & target file names
        tgtFileDict = dict(zip(srcFileList, tgtFileList))
        # Loop on jpegs, open each & save as xcf
        for srcFile in srcFileList:
            tgtFile = os.path.join(tgtPath, tgtFileDict[srcFile])
            srcFile = os.path.join(srcPath, srcFile)
            theImage = pdb.file_jpeg_load(srcFile, srcFile)
            
            PropWrite(theImage, propList)
            processImage(theImage)
            theDrawable = theImage.active_drawable
            # Set Flag Properties / Parasites
            pdb.gimp_xcf_save(0, theImage, theDrawable, tgtFile, tgtFile)
            pdb.gimp_image_delete(theImage)
                    
#
############################################################################
#
register (
    "python_fu_batchSaveJpgToXcfAutoCrop",         # Name registered in Procedure Browser
    "Convert jpg files to xcf", # Widget title
    "Convert jpg files to xcf", # 
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "Convert JPG to XCF (Directory)", # Menu Entry
    "",     # Image Type - No Image Loaded
    [
    ( PF_DIRNAME, "srcPath", "JPG Originals (source) Directory:", jpegDir ),
    ( PF_DIRNAME, "tgtPath", "XCF Working (target) Directory:", xcfDir ),
    ],
    [],
    batchSaveJpgToXcfAutoCrop,      # Matches to name of function being defined
    menu = "<Image>/DVIA"   # Menu Location
    )   # End register
#
main() 

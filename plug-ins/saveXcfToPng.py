#! /usr/bin/env python
#
############################################################################
#
from gimpfu import *
from gimpenums import *

import sys, os
import pickle
import pygtk
import re

pygtk.require("2.0")
import gtk


# Constants used by the script
PNG_WIDTH   = 250
PNG_HEIGHT  = 250
CLS_IDS     = {'catchall' : 0, 'stair' : 1, 'curb' : 2, 'doorframe': 3} #, 'badfloor': 4, 'drop': 5 }
CLASSES     = ['catchall', 'stair', 'curb', 'doorframe'] #, 'badfloor', 'drop']
MLC_LBLS    = [0, 0, 0, 0] #, 0, 0]
LABELFILE   = 'labels'


#############################################################################
# For GUI directory options.
xcfDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia")
#
# For GUI extra options. See description of saveXcfToPng for details
saveNP     = False
saveMLC    = False
saveLabels = False

SIG_OK     = -5
SIG_CANCEL = -6
SIG_YES    = -8 
SIG_NO     = -9

def questionBox(msg):
    btype=gtk.MESSAGE_QUESTION
    flag = gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_YES_NO, msg)
    resp = msgBox.run()
    msgBox.destroy()
    return resp

def msgBox(msg, btype=gtk.MESSAGE_INFO):
    flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
    msgBox.run()
    msgBox.destroy()

def mymsg(msg):
    #print msg
    pass


'''
This class takes an image filename as input, and stores a converted PNG image
into tgtdir. Apart from that, writes the labels data in labels file.
'''
class ImageExtractor:

    def __init__(self, srcdir, tgtdir, filelist, NP, MLC, OnlyLabels):
        self.srcdir     = srcdir
        self.tgtdir     = tgtdir
        self.filelist   = filelist
        self.NP         = NP
        self.MLC        = MLC
        self.OnlyLabels = OnlyLabels

    def run(self):
        if(self.NP):
            if(self.MLC):
                LABELFILE = 'labels_NP_MLC'
            else:
                LABELFILE = 'labels_NP'
        else:
            if(self.MLC):
                LABELFILE = 'labels_MLC'
            else:
                LABELFILE = 'labels'
        LABELFILE += '.txt'
        print LABELFILE
        self.lfile  = open(os.path.join(self.tgtdir, LABELFILE), 'w')
        for srcfile in self.filelist:
            mymsg("Converting {} to PNG.".format(srcfile))
            if not srcfile.lower().endswith('.xcf'):
                continue # skip non-xcf files
            if not self.extract(srcfile):
                msgBox('Could not extract labels and save image {}. Exiting.'.format(srcfile), gtk.MESSAGE_ERROR)
                return
        self.lfile.close()
        return

    def extract(self, filename):
        '''Public function. This function should be called for each image.
        '''
        self.basename = '.'.join(filename.split('.')[:-1]) ## Remove extension
        srcfilepath   = os.path.join(self.srcdir, filename)
        self.pngname  = '{}.png'.format(self.basename)

        # Original img with all layers
        self.img = pdb.gimp_file_load(srcfilepath, srcfilepath)
        self.base = pdb.gimp_image_get_layer_by_name(self.img, 'base')
        self.grp = pdb.gimp_image_get_layer_by_name(self.img, 'group')

        pdb.gimp_context_set_background('#000000')
        pdb.gimp_context_set_foreground('#ffffff')

        para = self.img.parasite_find('ldata')
        if not para:
            msgBox('Cannot find ldata parasite in the image {}. Did you run the image through proper flow?'.format(filename), gtk.MESSAGE_ERROR)
            return False
        self.ldata = pickle.loads(para.data)
        self.labels = self.ldata['labels']
        self.layers = self.ldata['layers']
        self.nps = self.ldata['NP']
        self.bbs = self.ldata['BB']

        nplbl = None
        xmax  = 0
        for lbl in self.nps:
            if len(self.nps[lbl]) > 0:
                if self.nps[lbl][0] >= xmax:
                    nplbl = lbl

        # If nplbl is still None, that means we didn't find any NP. Image didn't have an NP.
        if self.NP and nplbl is None:
            msgBox("Error: Couldn't find any Nearest Point data in the image. Disable saving NP if these are images without NPs.", gtk.MESSAGE_ERROR)
            return False

        labelstr = ''
        if not self.MLC: # Need to save label for one class and one NP
            labelstr = '{} {}'.format(self.pngname, CLS_IDS[nplbl])
            if self.NP:
                # Add NP x and y coordinates
                # Shiva : normalize x and y co-ordinate values
                x, y = map(float, self.nps[nplbl])
                x = float(x/self.img.height)
                y = float(y/self.img.width)
                labelstr += ' ' + ''.join(str(round(x, 3)))
                labelstr += ' ' + ''.join(str(round(y, 3)))
        else: # Need to save multi-label class format and multiple NPs
            labelstr = self.pngname
            cls = MLC_LBLS
            npstr = ''
            for lbl in self.labels:
                if self.labels[lbl]:
                    cls[CLS_IDS[nplbl]] = 1
                    if self.NP:
                        # Accumulate all NP x and y coordinates
                        if len(self.nps[lbl]) == 0:
                            msgBox('For label {l} in image {i}, could not find NP'.format(i=self.basename, l=lbl), gtk.MESSAGE_ERROR)
                            return False
                        # normalize the value here whenever self.nps happens
                        npstr += ' ' + ' '.join(map(lambda x:str(x), self.nps[lbl]))
            labelstr += ' ' + ' '.join(map(lambda x: str(x), cls))
            if self.NP:
                labelstr += npstr
        self.lfile.write('{}\n'.format(labelstr))
        if not self.OnlyLabels:
            self.saveImage()
        return True

    def flattenImage(self):
        pdb.gimp_image_reorder_item(self.img, self.base, None, -1) # Move base layer to the top; obscuring everything else...
        self.base = pdb.gimp_image_flatten(self.img) # ... and flatten the image to remove other layers
        self.base.name = 'base'

    def saveImage(self):
        '''Save as PNG image using tgtdir and basename
        '''
        fname = os.path.join(self.tgtdir, '{}.png'.format(self.basename))
        try:
            compression = 9;
            pdb.gimp_image_scale(self.img, PNG_WIDTH, PNG_HEIGHT)
            self.flattenImage()
            pdb.file_png_save(self.img, self.base, fname, fname, 0, compression, 0, 0, 0, 0, 0)
        except:
            msgBox('Could not save image {}: {}'.format(fname, sys.exc_info()[0]), gtk.MESSAGE_ERROR)
            raise
        pdb.gimp_image_delete(self.img)



def saveXcfToPng(srcdir, NP, MLC, OnlyLabels):
    """
    Registered function; Converts all of the Xcfs in the source 'augmented' 
    directory into rescaled PNG files in a target directory. Saves labels too.
    Source type dir name 'augmented' is enforced.
    NP : If true, saves Nearest points; if false, NPs are not saved
    MLC: IF true, saves all class labels; if false, only one class is saved.
    # In case of MLC=False, the class with NP closest to the bottom is selected automatically
    """
    srcAugDir = os.path.realpath(srcdir)
    aug       = srcdir.split('/')[-1]
    tgtPngDir = os.path.join('/'.join(srcAugDir.split('/')[:-1]), 'png')

    if aug != 'augmented':
        msgBox("Source type dir ({}) is not named 'augmented'. As a part of the flow, this is a requirement. Aborting!".format(aug), gtk.MESSAGE_ERROR)
        return

    if not os.path.exists(tgtPngDir):
        os.mkdir(tgtPngDir)
    labels = os.listdir(srcAugDir)
    labels.sort()
    for label in labels:
        tgtdir    = os.path.join(tgtPngDir, label)
        if os.path.exists(tgtdir):
            # Make sure that directory is empty. Otherwise quit.
            flist = os.listdir(tgtdir)
            if len(flist) > 0:
                resp = questionBox("Target directory {} is not empty. \n\n\tContinue?".format(tgtdir))
                if resp == SIG_YES:
                    #msgBox("You chose to continue ({})".format(resp))
                    pass
                else:
                    msgBox("You chose not to continue ({})".format(resp))
                    return
        else:
            os.mkdir(tgtdir)

    # At this point everything is in order. Start the conversion...
    msgBox("Images from following class directories in source 'augmented' dir will be converted to PNG: {}".format(labels), gtk.MESSAGE_INFO)

    # Find all of the files in the source directory
    for label in labels:
        tgtdir    = os.path.join(tgtPngDir, label)
        srcdir    = os.path.join(srcAugDir, label)
        filelist  = os.listdir(srcdir)
        filelist.sort()
        if len(filelist) == 0:
            continue
        mymsg("Converting {} directory to PNG.".format(label))
        extractor = ImageExtractor(srcdir, tgtdir, filelist, NP, MLC, OnlyLabels)
        extractor.run()
        mymsg("{} directory is converted to PNG.".format(label))

    mymsg("The PNG files and {} are successfully created in {}".format(LABELFILE, tgtPngDir))

#
############################################################################
#
register (
    "saveXcfToPng",           # Name registered in Procedure Browser
    "Convert XCF images from source 'augmented' directory to output PNG images in target 'png' directory. Includes extraction of labels.",       # Widget title
    "Convert XCF images from source 'augmented' directory to output PNG images in target 'png' directory. Includes extraction of labels.",
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "March 2016",             # Date
    "4. Convert XCF to Final PNG for DB",  # Menu Entry
    "",     # Image Type
    [
    ( PF_DIRNAME, "srcdir", "Input 'augmented' Directory:", xcfDir ),
    ( PF_BOOL,    "NP",     "Save Nearest Point as a label?", saveNP),
    ( PF_BOOL,    "MLC",    "Save labels in Multi-Label Classification (MLC) format?", saveMLC),
    ( PF_BOOL,    "OnlyLabels",    "Save Only Labels? ", saveLabels)
    ],
    [],
    saveXcfToPng,   # Matches to name of function being defined
    menu = "<Image>/DVIA/DirectoryLevelOps"  # Menu Location
    )   # End register

main() 

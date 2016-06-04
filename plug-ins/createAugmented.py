#! /usr/bin/env python
#
# This script takes as input a set of Gimp XCF files and creates a new 
# directory with augmented images for CNN training purposes
# Following transformations are applied to each image:
#
#  1. Salt-and-pepper noise 
#  2. Blur 
#  3. Sharpen 
#  4. Erode 
#  5. Dilate 
#  6. Soft-glow (light effects) 
#  7. Rotation (up to 30 degrees) 
#  8. Perspective distortion (how much?) 
#  9. Resize (different object sizes, while retaining same image size)
# 10. Shifts (pan)
#
# Each transformation is used with different parameters to create 4-6 images each.
# This create about 40 augmented images per 1 original image.
#
############################################################################
#
from gimpfu import *
from gimpenums import *

import sys, os
from glob import glob
import pickle
import pygtk
import re

pygtk.require("2.0")
import gtk

PI = 3.14159265358979323846

# Constants used by the script
PNG_WIDTH   = 300
PNG_HEIGHT  = 400
CLS_IDS     = {'stair' : 1, 'curb' : 2, 'doorframe': 3} #, 'badfloor': 4, 'drop': 5 } ## catchall should be ignored
CLASSES     = ['stair', 'curb', 'doorframe'] #, 'badfloor', 'drop']                   ## ditto
MLC_LBLS    = [0, 0, 0] #, 0, 0]   ## no place for catchall: All zeros mean full catchall/background image
LABELFILE   = 'labels'


#
origDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia/xcf")
#

#scriptpath = os.path.dirname(os.path.realpath( __file__ ))
#scriptrootdir  = os.path.sep.join(scriptpath.split(os.path.sep)[:-4])
#sys.stderr = open(os.path.join(os.environ['HOME'], '/tmp/augmenter_stderr.log'), 'w')
#sys.stdout = open(os.path.join(os.environ['HOME'], '/tmp/augmenter_stdout.log'), 'w')

def msgBox(msg, btype=gtk.MESSAGE_INFO):
    flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
    msgBox.run()
    msgBox.destroy()

def questionBox(msg):
    btype=gtk.MESSAGE_QUESTION
    flag = gtk.DIALOG_DESTROY_WITH_PARENT
    msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_YES_NO, msg)
    resp = msgBox.run()
    msgBox.destroy()
    return resp

def mymsg(msg):
    #print msg
    pass


'''
This class takes a single XCF directory as input, and stores new images into tgtdir
'''
class ImageAugmentor:

    def __init__(self, srcdir, tgtdir, filelist, NP, MLC, OnlyLabels):
        self.srcdir = srcdir
        self.tgtdir = tgtdir
        self.filelist   = filelist
        self.NP         = NP
        self.MLC        = MLC
        self.OnlyLabels = OnlyLabels

    def run(self):
        # Inspite of this if-then-else, a labels.txt without NP/MLC is always saved.
        if self.NP:
            if self.MLC:
                LABELFILE = 'labels_NP_MLC'
            else:
                LABELFILE = 'labels_NP'
        else:
            if self.MLC:
                LABELFILE = 'labels_MLC'
            else:
                LABELFILE = 'labels'
        LABELFILE += '.txt'
        self.lfile   = open(os.path.join(self.tgtdir, LABELFILE), 'w')
        self.lfile2  = open(os.path.join(self.tgtdir, 'labels.txt'), 'w')

        for srcfile in self.filelist:
            if not self.augment(srcfile):
                msgBox('Could not augment DB for image {}. Exiting.'.format(srcfile), gtk.MESSAGE_ERROR)
                return False
        self.lfile.close()
        self.lfile2.close()
        return True

    def augment(self, filename):
        '''This function should be called for each image.
        '''
        basefilename = filename.split('/')[-1]
        self.basename = '.'.join(basefilename.split('.')[:-1]) ## Remove extension
        srcfilepath = filename # os.path.join(self.srcdir, filename)

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
        if self.labels['catchall']:
            self.nps = {'catchall' : (self.img.width/2, self.img.height/2), 'stair' : (), 'curb' : (), 'doorframe': () } #, 'badfloor': () }
            self.bbs = {'catchall' : (0,0, self.img.width,self.img.height), 'stair' : (), 'curb' : (), 'doorframe': () } #, 'badfloor': () }
            self.ldata['NP'] = self.nps
            self.ldata['BB'] = self.bbs
            self.img.attach_new_parasite('ldata', 5, pickle.dumps(self.ldata)) # Update the image parasites for later use 

        self.nps = self.ldata['NP']
        self.bbs = self.ldata['BB']

        # Augmentor routines
        if not self.augNoise():
            return False
        if not self.augBlur():
            return False
        if not self.augSharpen():
            return False
        if not self.augErode():
            return False
        if not self.augDilate():
            return False
        if not self.augGlow():
            return False
        if not self.augRotation():
            return False
        if not self.augPerspDistort():
            return False
        if not self.augScale():
            return False
        if not self.augPan():
            return False

        # Save base image
        self.saveImage(self.img, '00_BASE_IMAGE', updateParasites=False)
        return True

    ## Local functions. Not to be called directly
    def augNoise(self):
        '''Add Noise
        '''

        for noiseAmount in (0.10, 0.18, 0.23, 0.28):
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            try:
                pdb.plug_in_noisify(nimg, nimg.active_drawable, 0, noiseAmount, 0,0,0)
            except:
                msgBox('augNoise failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            self.saveImage(nimg, '00_noise_{:4.2f}'.format(noiseAmount)) # Save image and delete from memory
        return True

    def augBlur(self):
        '''Blur the image
        '''
        try:        
            # Gaussian blur. Similar to soft focus
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_gauss_iir(nimg, nimg.active_drawable, 3, 1, 2)
            self.saveImage(nimg, '01_blur1_gaussblur1')

            # Gaussian blur. More
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_gauss_iir(nimg, nimg.active_drawable, 4, 2, 2)
            self.saveImage(nimg, '01_blur2_gaussblur2')

            # Linear motion blur, vertical shake
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_mblur(nimg, nimg.active_drawable, 0, 6, 100, 0, 0)
            self.saveImage(nimg, '01_blur3_mblur_ver')

            # Linear motion blur, horizontal shake
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_mblur(nimg, nimg.active_drawable, 0, 6, 12, 0, 0)
            self.saveImage(nimg, '01_blur4_mblur_hor')

            # Radial motion blur, towards center
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_mblur(nimg, nimg.active_drawable, 1, 0.13, 1.9, 100, 100)        
            self.saveImage(nimg, '01_blur5_mblur_rcnt')

            # Radial motion blur, completely off-center
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_mblur(nimg, nimg.active_drawable, 1, 0.00, 1.00, -20, -10)
            self.saveImage(nimg, '01_blur6_mblur_rshk1')

            # Radial motion blur, completely off-center, larger shake
            nimg = pdb.gimp_image_duplicate(self.img)
            pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            pdb.plug_in_mblur(nimg, nimg.active_drawable, 1, 0.12, 1.1, -100, 300)
            self.saveImage(nimg, '01_blur7_mblur_rshk2')

            # Radial motion blur, completely off-center, even larger shake, different direction
            # Shiva - commenting this out as this image type is not helpful,
            # most of the info in the image goes away - Shiva
            #nimg = pdb.gimp_image_duplicate(self.img)
            #pdb.gimp_image_set_active_layer(nimg, pdb.gimp_image_get_layer_by_name(nimg, 'base'))
            #pdb.plug_in_mblur(nimg, nimg.active_drawable, 1, 0.2, 1.27, 800, -800)
            #self.saveImage(nimg, '01_blur8_mblur_rshk3')
        except:
            msgBox('augBlur failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
            raise
            return False

        return True

    def augSharpen(self):
        '''Sharpen the image
        '''
        idx = 1
        for (r, amt) in (( 8, 0.3),  # Low
                         ( 5, 0.6),  # Small radius medium
                         (10, 0.8),  # Wider radius medium (affects contrast)
                         (60, 1.0)): # High contrast
            nimg = pdb.gimp_image_duplicate(self.img)
            base = pdb.gimp_image_get_layer_by_name(nimg, 'base')
            grp  = pdb.gimp_image_get_layer_by_name(nimg, 'group')
            pdb.gimp_image_reorder_item(nimg, base, None, -1) # Move base layer to the top; obscuring everything else...
            pdb.gimp_image_set_active_layer(nimg, base)
            try:
                pdb.plug_in_unsharp_mask(nimg, base, r, amt, 0)
            except:
                msgBox('augSharpen failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            pdb.gimp_image_reorder_item(nimg, base, grp, 20) # Move base layer to the bottom of grp
            self.saveImage(nimg, '02_sharp{}'.format(idx)) # Save image and delete from memory
            idx = idx + 1

        return True

    def augErode(self):
        '''Filter with erosion filter (shrinks white -- or groes white area)
        '''
        nimg = []
        rnge = (0, ) # Note: doing only one iteration. Since the size change to 300x300, two iterations are too much
        #rnge = (0, 1)
        for idx in rnge:
            nimg.append(pdb.gimp_image_duplicate(self.img))
            base = pdb.gimp_image_get_layer_by_name(nimg[idx], 'base')
            for rep in range(0, idx+1):
                # Erode idx+1 times
                try:
                    pdb.plug_in_erode(nimg[idx], base, 0, 0, 0, 0 , 0, 0)
                except:
                    msgBox('augErode failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                    raise
                    return False
            self.saveImage(nimg[idx], '03_erode{}'.format(idx)) # Save image and delete from memory

        return True

    def augDilate(self):
        '''Filter with dilate filter
        '''
        nimg = []
        rnge = (0, ) # Note: doing only one iteration. Since the size change to 300x300, two iterations are too much
        #rnge = (0, 1)
        for idx in rnge:
            nimg.append(pdb.gimp_image_duplicate(self.img))
            base = pdb.gimp_image_get_layer_by_name(nimg[idx], 'base')
            for rep in range(0, idx+1):
                # Dilate idx+1 times
                try:
                    pdb.plug_in_dilate(nimg[idx], base, 0, 0, 0, 0, 0, 0)
                except:
                    msgBox('augDilate failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                    raise
                    return False
            self.saveImage(nimg[idx], '04_dilate{}'.format(idx)) # Save image and delete from memory

        return True

    def augGlow(self):
        '''Add soft glow to image. A lighting effect. Can also happen with a foggy lens.
        '''
        idx = 1
        for (r, brightness, sharpness) in ((20, 0.40, 1.40),
                                           (10, 0.50, 0.50),
                                           (10, 0.65, 0.85),
                                           ( 5, 0.70, 0.40),
                                           (20, 0.85, 0.30)):
            nimg = pdb.gimp_image_duplicate(self.img)
            base = pdb.gimp_image_get_layer_by_name(nimg, 'base')
            try:
                pdb.plug_in_softglow(nimg, base, r, brightness, sharpness)
            except:
                msgBox('augGlow failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            self.saveImage(nimg, '05_glow{}'.format(idx)) # Save image and delete from memory
            idx = idx + 1

        return True

    def augRotation(self):
        '''Rotate image. After rotation, corners may get filled with background color is image layer is not large
        enough compared to the RoI mask. This function will make the background color black.
        '''

        idx  = 0
        snpx = 0
        snpy = 0
        for lbl in self.nps:
            if len(self.nps[lbl]) > 0:
                idx += 1
                (npx, npy) = self.nps[lbl]
                snpx += npx
                snpy += npy
        npx = snpx/idx
        npy = snpy/idx

        # Find average of npx and npy. This gives us our center of rotation
        w = self.img.width
        if (w/3 - npx) > 0:     # On the left 1/3
            # More CW rotation than CCW
            angles = (-4, 4, 7, 10)
        elif (npx - 2*w/3) > 0: # On the right 1/3
            # More CCW rotation than CW
            angles = (-10, -7, -4, 4)
        else:
            # Symmetrical rotation
            angles = (-7, -4, 4, 7)
        idx = 1
        for angle in angles:
            nimg = pdb.gimp_image_duplicate(self.img)
            grp = pdb.gimp_image_get_layer_by_name(nimg, 'group')
            pdb.gimp_selection_all(nimg) # Rotation works best with a selection as coordinates match up
            try:
                pdb.gimp_item_transform_rotate(grp, float(PI*angle/360), False, npx, npy)
            except:
                msgBox('augRotate failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            sangle = re.sub('-', 'n', str(int(angle)))
            self.saveImage(nimg, '06_rotate{}_{}'.format(idx, sangle)) # Save image and delete from memory
            idx += 1
        return True

    def augPerspDistort(self):
        '''Add perspective distortion to the image. Background filled with black as appropriate.
        '''
        w = self.img.width
        h = self.img.height
        # Format: positive is inside the image (shrink), negative is outside the image (expand);
        # All values are to be added of substracted from img width and height
        idx = 1
        for ((x0,y0),(x1,y1), (x2,y2), (x3,y3)) in (((12,0),    (12,0),    (0,0),   (0,0)), # move top-right corner 10pix to the right; top-left corner 10px to left; bottom-right and bottom-left are left untouched 
                                                    ((22,0),    (22,0),    (0,0),   (0,0)),
                                                    ((12,0),    (12,0),    (-10,0), (-10,0)),
                                                    ((17,0),    (17,0),    (-17,0), (-17,0)),
                                                    ((12,12),   (-12,-12), (0,0),   (0,0)), 
                                                    ((-12,-12), (12,12),   (-12,0), (-12,0))):
            nimg = pdb.gimp_image_duplicate(self.img)
            grp  = pdb.gimp_image_get_layer_by_name(nimg, 'group')
            pdb.gimp_selection_all(nimg)
            try:
                pdb.gimp_item_transform_perspective(grp, x0,y0, w-x1,y1, x2,h-y2, w-x3,h-y3)
            except:
                msgBox('augPerspDistort failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            self.saveImage(nimg, '07_perspective{}'.format(idx)) # Save image and delete from memory
            idx += 1
        return True

    def augScale(self):
        '''Scales image to simulate different object sizes. The final image size is kept unchanged.
        After scaling, unoccupied areas will be filled with black background
        '''
        w = self.grp.width
        h = self.grp.height
        (x0,y0) = self.grp.offsets
        idx = 1
        for scale in (-10, 10, 20, 30):
            nimg = pdb.gimp_image_duplicate(self.img)
            grp  = pdb.gimp_image_get_layer_by_name(nimg, 'group')
            try:
                pdb.gimp_item_transform_scale(grp, x0+scale,y0+scale, x0+w-scale, y0+h-scale)
            except:
                msgBox('augScale failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            self.saveImage(nimg, '08_scale{}'.format(idx)) # Save image and delete from memory
            idx += 1
        return True

    def augPan(self):
        '''Pan the image by a few pixels in all four directions
        This routine uses gimp_item_transform_scale similar to augScale. However, here it is
        used only to pan the grp layer around
        '''
        nparray = []
        for lbl in self.nps:
            if len(self.nps[lbl]) > 0:
                nparray.append(self.nps[lbl])
        (xmax,ymax) = max(nparray)
        (xmin,ymin) = min(nparray)

        # Determine x and y offsets based on min and max of the NPs.
        # This is not full-proof. Just an attempt to minimize the problem of pushing the NP out of the image
        w = self.grp.width
        h = self.grp.height
        # x and y offsets are with respect to the top-right corner of the image. neg means move left, pos means move right
        if (w - xmax) < 20:    # close to right edge
            xoffsets = (-24, -16, -8, 8)
        elif xmin < 20:        # close to left edge
            xoffsets = (-8, 8, 16, 24)
        else:                   # enough margin on both sides
            xoffsets = (-16, -8, 8, 16)

        if (h - ymax) < 20:    # close to bottom edge
            yoffsets = (-24, -16, -8, 8)
        elif ymin < 20:        # close to top edge
            yoffsets = (-8, 8, 16, 24)
        else:
            yoffsets = (-16, -8, 8, 16)

        (x0,y0) = self.grp.offsets
        idx = 1
        for (x,y) in zip(xoffsets, yoffsets):
            nimg = pdb.gimp_image_duplicate(self.img)
            grp  = pdb.gimp_image_get_layer_by_name(nimg, 'group')
            try:
                pdb.gimp_item_transform_scale(grp, x0+x,y0+y, x0+w+x, y0+h+y)
            except:
                msgBox('augPan failed: {}'.format(sys.exc_info()[0]), gtk.MESSAGE_ERROR)
                raise
                return False
            self.saveImage(nimg, '09_pan{}'.format(idx)) # Save image and delete from memory
            idx += 1
        return True

    #####################################################################################
    # Utility functions
    #####################################################################################
    def updateParasites(self, img):
        '''Goes through the layers to find new coardinates for BBs and NPs and updates
        parasites accordingly. If the BBs and/or NPs are not found, silently ignores that
        and keeps old coordinates in the parasites
        '''
        para   = img.parasite_find('ldata')
        ldata  = pickle.loads(para.data)
        labels = ldata['labels']
        
        for lbl in labels:
            if not labels[lbl]:
                continue
            # At this point, we know that label lbl exists
            for ltype in ('bb', 'np'):
                lname = "{}_{}".format(lbl,ltype)
                lyr   = pdb.gimp_image_get_layer_by_name(img, lname)
                if not lyr: # Found layer
                    print 'Layer {} for img {} not found. Skipping the layer silently'.format(lname, str(img))
                    continue
                pdb.gimp_image_select_item(img, CHANNEL_OP_REPLACE, lyr)
                # Get new selection bounding box 
                bbox = pdb.gimp_selection_bounds(img)
                if bbox[0] == 0:
                    # Empty selection -- can happen if the NP or BB moved out of the image range due to transformation. Also for catchall image class
                    #print 'Bounding box for label {l} {t} for img {i} not found. Skipping the {t} update silently'.format(l=lbl, t=ltype.upper(), i=str(img))
                    continue # skip further operation
                if ltype == 'bb':
                    ldata['BB'][lbl] = bbox[1:]
                else:
                    ldata['NP'][lbl] = (bbox[1] + (bbox[3]-bbox[1])/2, bbox[4]) # Bottom center of bb
                pdb.gimp_selection_none(img)
    
        self.ldata = ldata
        #try: img.attach_new_parasite('ldata', 5, pickle.dumps(ldata))
        #except:
        #    msgBox('Could not save ldata parasite for image {}: {}'.format(str(img), sys.exc_info()[0]), gtk.MESSAGE_ERROR)
        #    raise
        #    return

    def appendLabelsFile(self, img, fname):
        '''
        Extract parasites to update labels file and save image
        '''
        #para = img.parasite_find('ldata')
        #self.ldata = pickle.loads(para.data)
        self.labels = self.ldata['labels']
        self.layers = self.ldata['layers']
        self.nps = self.ldata['NP']
        self.bbs = self.ldata['BB']

        nplbl = None
        ymax  = 0
        for lbl in self.nps:
            if len(self.nps[lbl]) > 0:
                if self.nps[lbl][1] >= ymax:
                    nplbl = lbl
                    ymax = self.nps[lbl][1]

        # If nplbl is still None, that means we didn't find any NP. Image didn't have an NP.
        if nplbl is None:
            print "Error! NP data not found!"
            return False

        labelstr = '{} {}'.format(fname, CLS_IDS[nplbl])
        self.lfile2.write('{}\n'.format(labelstr))
        if not self.MLC: # Need to save label for one class and one NP
            if self.NP:
                # Add NP x and y coordinates
                # Normalize x and y co-ordinate values
                x, y = map(float, self.nps[nplbl])
                x = round(x/self.img.width, 3)
                y = round(y/self.img.height, 3)
                labelstr += ' {} {}'.format(x, y)
        else: # Need to save multi-label class format and multiple NPs
            labelstr = fname
            cls = MLC_LBLS
            npstr = ''
            for lbl in self.labels:
                if self.labels[lbl]:
                    cls[CLS_IDS[nplbl]] = 1
                    if self.NP:
                        # Accumulate all NP x and y coordinates
                        if len(self.nps[lbl]) == 0:
                            print 'Error! For label {l} in image {i}, could not find NP'.format(i=self.basename, l=lbl)
                            return False
                        # Normalize x and y co-ordinate values
                        x, y = map(float, self.nps[lbl])
                        x = round(x/self.img.width, 3)
                        y = round(y/self.img.height, 3)
                        npstr += ' {} {}'.format(x, y)
                        #npstr += ' ' + ' '.join(map(lambda x:str(round(float(x)/float(self.img.width), 3)), self.nps[lbl]))
            labelstr += ' ' + ' '.join(map(lambda x: str(x), cls))
            if self.NP:
                labelstr += npstr
        self.lfile.write('{}\n'.format(labelstr))
        return True


    def getImageFlatCopy(self, img):
        limg = pdb.gimp_image_duplicate(img) # local copy of the image
        base = pdb.gimp_image_get_layer_by_name(limg, 'base')
        pdb.gimp_image_reorder_item(limg, base, None, -1) # Move base layer to the top; obscuring everything else...
        nlyr = pdb.gimp_image_flatten(limg) # ... and flatten the image to remove other layers
        nlyr.name = 'base'
        return limg

    def flattenImage(self, img):
        # Move base layer to the top; obscuring everything else ...
        pdb.gimp_image_reorder_item(img, pdb.gimp_image_get_layer_by_name(img, 'base'), None, -1)
        # ... and flatten the image to remove other layers
        base = pdb.gimp_image_flatten(img)
        base.name = 'base'
        return base

    def saveImage(self, img, suffix, updateParasites=False):
        '''
        Save image using tgtDir, basename, and suffix. Conditionally update the parasites
        Also append labels data to labels file/s
        '''
        basename = '{}_{}.png'.format(self.basename, suffix)
        fname = os.path.join(self.tgtdir, basename)
        self.updateParasites(img)
        if not self.appendLabelsFile(img, basename):
            msgBox("Error: Problem finding label data. Abort!", gtk.MESSAGE_ERROR)
            raise

        try:
            compression = 9;
            pdb.gimp_image_scale(img, PNG_WIDTH, PNG_HEIGHT)
            base = self.flattenImage(img)
            pdb.file_png_save(img, base, fname, fname, 0, compression, 0, 0, 0, 0, 0)
        except:
            msgBox('Could not save image {}: {}'.format(fname, sys.exc_info()[0]), gtk.MESSAGE_ERROR)
            raise
        pdb.gimp_image_delete(img)



def createAugmented(srcdir, MLC):
    """Registered function; Creates augmented images based on original labeled set of images.
    Operates on all images in srcdir directory to create images in a parallel 'augmented' directory.
    NP : If true, saves Nearest points; if false, NPs are not saved
    MLC: IF true, saves all class labels; if false, only one class is saved.
    # In case of MLC=False, the class with NP closest to the bottom is selected automatically
    """
    NP         = True
    OnlyLabels = False

    xcfdir    = os.path.realpath(srcdir)
    xcf       = srcdir.split('/')[-1]
    tgtAugdir = os.path.join('/'.join(xcfdir.split('/')[:-1]), 'augmented')

    if xcf != 'xcf':
        msgBox("Source dir ({}) is not named 'xcf'.\nThis is a requirement as a part of the flow. Aborting!".format(xcf), gtk.MESSAGE_ERROR)
        return

    if not os.path.exists(tgtAugdir):
        os.mkdir(tgtAugdir)

    labels_ = os.listdir(xcfdir)
    labels_.sort()
    filelists = {}
    labels = []
    # Consider only non-empty directories (useful visual check for the user when these dirs are shown)
    for label in labels_:
        srcdir    = os.path.join(xcfdir, label)
        filelist  = glob(srcdir+os.path.sep+'*.xcf')
        if len(filelist) == 0:
            continue
        filelist.sort()
        filelists[label] = filelist # store sorted filelist
        labels.append(label)

    # Each non-empty directory in source 'xcf/*', will be augmented.
    # If the corresponding dir in 'augmented' dir is non-empty, this script will abort.
    # NOTE: To avoid a certain directory from being augmented, temporarily move it out of the 'xcf' directory 
    #       before running this script and move back later. This is a workaround for incremental augmentation
    #       or in the case of a merged 'xcf' directory.
    for label in labels:
        tgtdir    = os.path.join(tgtAugdir, label)
        if os.path.exists(tgtdir):
            # Make sure that directory is empty. Otherwise quit.
            flist = os.listdir(tgtdir)
            if len(flist) > 0:
                msgBox("Target dir {} is not empty. Aborting!".format(tgtdir), gtk.MESSAGE_ERROR)
                return # quit if non-empty directory is found.
        else:
            os.mkdir(tgtdir)

    # At this point everything is in order. Start the augmentation...
    msgBox("Images from following directories will be augmented:\n\t{}".format(labels), gtk.MESSAGE_INFO)

    # Find all of the files in the source directory
    for label in labels:
        tgtdir    = os.path.join(tgtAugdir, label)
        srcdir    = os.path.join(xcfdir, label)
        filelist  = filelists[label]
        print("Augmenting {} directory.".format(label))
        aug = ImageAugmentor(srcdir, tgtdir, filelist, NP, MLC, OnlyLabels)
        if not aug.run():
            return
        print("{} directory is augmented.".format(label))

    print("The augmented PNG files and {} are successfully created in {}".format(LABELFILE, tgtAugdir))



# For GUI options.
saveMLC    = False

#
############################################################################
#
register (
    "createAugmented",     # Name registered in Procedure Browser
    "Create augmented images for CNN training (saved as PNG)", # Widget title
    "Create augmented images for CNN training (saved as PNG).",
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "May 2016",               # Date
    "3. Create Augmented Images (PNG)", # Menu Entry
    "",     # Image Type
    [
    ( PF_DIRNAME, "srcdir", "Source Directory Containing Labeled XCF Images:", origDir ),
    ( PF_BOOL,    "MLC",    "Save labels in Multi-Label Classification (MLC) format?", saveMLC),
    ],
    [],
    createAugmented,   # Matches to name of function being defined
    menu = "<Image>/DVIA/DirectoryLevelOps"  # Menu Location
    )   # End register

main() 

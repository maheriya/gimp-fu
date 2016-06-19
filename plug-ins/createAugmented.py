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
import pygtk
import XmlAnnotator
pygtk.require("2.0")
import gtk

import sys, os
from shutil import rmtree
from glob import glob
import pickle
import re
from dvia_common import *
from XmlAnnotator import XmlAnnotator


PI = 3.14159265358979323846

# Constants used by the script
PNG_WIDTH   = 300
PNG_HEIGHT  = 400
LABELFILE   = 'labels.txt'


#
origDir = os.path.join(os.environ['HOME'], "Projects/IMAGES/dvia/xcf")

'''
This class takes a single XCF directory as input, and stores new images into tgtdir
Also creates labels.txt and XML annotations.
'''
class ImageAugmentor:

    def __init__(self, srcdir, tgtdir, tgtAnndir, filelist, OnlyCheckParasites):
        self.srcdir     = srcdir
        self.tgtdir     = tgtdir
        self.tgtAnndir  = tgtAnndir
        #
        self.filelist   = filelist
        self.OnlyCheckParasites = OnlyCheckParasites

    def run(self):
        status = True
        if not self.OnlyCheckParasites:
            self.lfile  = open(os.path.join(self.tgtdir, LABELFILE), 'w')
        for srcfile in self.filelist:
            basefilename = srcfile.split('/')[-1]
            self.basename = '.'.join(basefilename.split('.')[:-1]) ## Remove extension

            if self.OnlyCheckParasites:
                print('Checking {}'.format(basefilename))
            else:
                print('Augmenting {}'.format(basefilename))
            ## Run the main routine
            if not self.augment(srcfile):
                status = False
                if self.OnlyCheckParasites:
                    print('Error! {} had issues with parasite data'.format(basefilename))
                else:
                    msgBox('Could not augment DB for image {}. Exiting.'.format(basefilename), gtk.MESSAGE_ERROR)
                    break

        if not self.OnlyCheckParasites:
            self.lfile.close()
            if status==False:
                # Clean up
                os.unlink(os.path.join(self.tgtdir, LABELFILE))
                if os.path.exists(self.tgtdir) and len(os.listdir(self.tgtdir))==0:
                    os.rmdir(self.tgtdir)
        return status

    def augment(self, filename):
        '''This function should be called for each image.
        '''
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
        self.objects  = self.ldata['objects']
        if self.labels['catchall']:
            self.objects['catchall'][0]['np'] = (self.img.width/2, self.img.height/2)
            self.objects['catchall'][0]['bb'] = (0,0, self.img.width,self.img.height)
            self.img.attach_new_parasite('ldata', 5, pickle.dumps(self.ldata)) # Update the image parasites for later use

        ####
        if self.OnlyCheckParasites:
            status = self.checkParasites()
            pdb.gimp_image_delete(self.img)
            return status
        ####
        
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
        # For each class
        for lbl in self.objects:
            # ... with objects
            if len(self.objects[lbl]) > 0:
                # ... sum up nps
                for obj in self.objects[lbl]:
                    idx += 1
                    (npx, npy) = obj['np']
                    snpx += npx
                    snpy += npy
        # ... to find geometric center of all nps. This gives us our center of rotation
        npx = snpx/idx
        npy = snpy/idx

        # Now adjust angles depending on where the center of nps lies 
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
        for lbl in self.objects:
            if len(self.objects[lbl]) > 0:
                for obj in self.objects[lbl]:
                    nparray.append(obj['np'])
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
    def checkParasites(self):
        '''
        Check parasites data to ensure images have valid data
        '''
        labels  = self.ldata['labels']
        objects = self.ldata['objects']
        status  = True

        # For MC (multi-class classification), only one class is exclusively put in labels file
        # We find the NP closest to the bottom of the image -- potentially closest to camera
        nplbl = None
        ymax  = 0
        for lbl in dvia_classes:
            if not labels[lbl]:
                continue
            for obj in objects[lbl]:
                if len(obj['np'])>0 and obj['np'][1] >= ymax:
                    nplbl = lbl
                    ymax = obj['np'][1]
        # If nplbl is still None, that means we didn't find any NP. Image didn't have an NP.
        if nplbl is None:
            print "\tError! NP data not found! ({})".format(self.basename)
            status = False

        for lbl in dvia_classes:
            if labels[lbl]:
                if len(objects[lbl])==0:
                    print '\tError! For label {l} in image {i}, could not find any object'.format(i=self.basename, l=lbl)
                    status = False
                for obj in objects[lbl]: # For all objects for the current label
                    if len(obj['np']) == 0:
                        print '\tError! For label {l} in image {i}, could not find NP'.format(i=self.basename, l=lbl)
                        status = False
                    ## Handle BB
                    if len(obj['bb']) == 0:
                        print '\tError! For label {l} in image {i}, could not find BB'.format(i=self.basename, l=lbl)
                        status = False
        return status

    def updateParasites(self, img):
        '''Goes through the layers to find new coordinates for BBs and NPs and updates
        parasites accordingly. If the BBs and/or NPs shapes are not found, silently ignores
        that and keeps old coordinates in the parasites
        '''
        para    = img.parasite_find('ldata')
        ldata   = pickle.loads(para.data)
        labels  = ldata['labels']
        objects = ldata['objects']

        for lbl in dvia_classes:
            if not labels[lbl]:
                continue
            # At this point, we know that label lbl exists
            for ltype in ('bb', 'np'):
                for obj in objects[lbl]:
                    lname = obj[ltype+'Layer']
                    lyr   = pdb.gimp_image_get_layer_by_name(img, lname)
                    if not lyr: # Found layer
                        print 'Layer {} for img {} not found. Keeping old {}.'.format(lname, img.name, ltype.upper())
                        continue
                    pdb.gimp_image_select_item(img, CHANNEL_OP_REPLACE, lyr)
                    # Get new selection bounding box 
                    bbox = pdb.gimp_selection_bounds(img)
                    if bbox[0] == 0:
                        # Empty selection -- can happen if the NP or BB moved out of the image range due to transformation. Also for catchall image class
                        #print 'Bounding box for label {l} {t} for img {i} not found. Skipping the {t} update silently'.format(l=lbl, t=ltype.upper(), i=str(img))
                        continue # skip further operation
                    (x1,y1,x2,y2) = bbox[1:]
                    w  = x2 - x1
                    h  = y2 - y1
                    xc = x1 + w/2
                    yc = y1 + h/2
                    if ltype == 'bb':
                        obj['bb'] = (x1,y1,x2,y2)
                    else:
                        obj['np'] = (xc, y2) # Bottom center of bb
                    pdb.gimp_selection_none(img)
    
        return ldata

    def appendLabelsFile(self, img, fname, ldata):
        '''
        Extract parasites to update labels file and save image
        '''
        labels = ldata['labels']
        objects = ldata['objects']
        
        # For MC (multi-class classification), only one class is exclusively put in labels file
        # We find the NP closest to the bottom of the image -- potentially closest to camera
        nplbl = None
        ymax  = 0
        for lbl in dvia_classes:
            if not labels[lbl]:
                continue
            for obj in objects[lbl]:
                if len(obj['np'])>0 and obj['np'][1] >= ymax:
                    nplbl = lbl
                    ymax = obj['np'][1]
        # If nplbl is still None, that means we didn't find any NP. Image didn't have an NP.
        if nplbl is None:
            print "Error! NP data not found!"
            return False

        labelstr = '{} {}'.format(fname, dvia_cls_ids[nplbl])
        self.lfile.write('{}\n'.format(labelstr))

        xann = XmlAnnotator(self.tgtAnndir, fname, self.img.width, self.img.height)
        # Need to save all objects to XML annotation file
        # The XML format supports multiple classes and multiple instances of BBs/NPs per class
        for lbl in dvia_classes:
            if labels[lbl]:
                if len(objects[lbl])==0:
                    print '\tError! For label {l} in image {i}, could not find any object'.format(i=self.basename, l=lbl)
                    return False
                for obj in objects[lbl]: # For all objects for the current label
                    if len(obj['np']) == 0:
                        print 'Error! For label {l} in image {i}, could not find NP'.format(i=self.basename, l=lbl)
                        return False
                    if len(obj['bb']) == 0:
                        print 'Error! For label {l} in image {i}, could not find BB'.format(i=self.basename, l=lbl)
                        return False
                    xann.addObject(lbl, obj)
        ## Create XML Annotation file
        xann.write()
        return True

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
        ldata = self.updateParasites(img)
        if not self.appendLabelsFile(img, basename, ldata):
            msgBox("Error: Problem finding label data for {}_{} Abort!".format(self.basename,suffix), gtk.MESSAGE_ERROR)
            raise

        try:
            compression = 9;
            #pdb.gimp_image_scale(img, PNG_WIDTH, PNG_HEIGHT)
            base = self.flattenImage(img)
            pdb.file_png_save(img, base, fname, fname, 0, compression, 0, 0, 0, 0, 0)
        except:
            msgBox('Could not save image {}: {}'.format(fname, sys.exc_info()[0]), gtk.MESSAGE_ERROR)
            raise
        pdb.gimp_image_delete(img)



def createAugmented(srcdir, onlycheckpara):
    """Registered function; Creates augmented images based on original labeled set of images.
    Operates on all images in srcdir directory to create images in a parallel 'augmented' directory.
    MLC: IF true, saves all class labels; if false, only one class is saved.
    # In case of MLC=False, the class with NP closest to the bottom is selected automatically
    """
    AllowExistingAugDir = False

    xcfdir    = os.path.realpath(srcdir)
    xcf       = srcdir.split('/')[-1]
    tgtAugdir = os.path.join('/'.join(xcfdir.split('/')[:-1]), 'augmented')
    tgtAnndir = os.path.join('/'.join(xcfdir.split('/')[:-1]), 'Annotations')

    if xcf != 'xcf':
        msgBox("Source dir ({}) is not named 'xcf'.\nThis is a requirement as a part of the flow. Aborting!".format(xcf), gtk.MESSAGE_ERROR)
        return

    if not onlycheckpara:
        if not os.path.exists(tgtAugdir):
            os.mkdir(tgtAugdir)
        if os.path.exists(tgtAnndir):
            rmtree(tgtAnndir)
        os.mkdir(tgtAnndir)

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

    if not onlycheckpara:
        # Each non-empty directory in source 'xcf/*', will be augmented.
        # If the corresponding dir in 'augmented' dir is non-empty, this script will abort (except if AllowExistingAugDir is True)
        # NOTE: To avoid a certain sub-directory from being augmented, temporarily move it out of the 'xcf' directory
        #       before running this script and move back later. This is a workaround for incremental augmentation
        #       or in the case of a merged 'xcf' directory.
        for label in labels:
            tgtdir    = os.path.join(tgtAugdir, label)
            if os.path.exists(tgtdir):
                # Make sure that directory is empty. Otherwise quit.
                flist = os.listdir(tgtdir)
                if len(flist) > 0:
                    if AllowExistingAugDir:
                        msgBox("Target dir is not empty. Continuing since AllowExistingAugDir=True", gtk.MESSAGE_ERROR)
                    else:
                        msgBox("Target dir {} is not empty. Aborting!".format(tgtdir), gtk.MESSAGE_ERROR)
                        return # quit if non-empty directory is found.
            else:
                os.mkdir(tgtdir)

    # At this point everything is in order. Start the augmentation...
    msgBox("Will process following directories:\n\t{}".format(labels), gtk.MESSAGE_INFO)

    # Find all of the files in the source directory
    status = True
    for label in labels:
        tgtdir    = os.path.join(tgtAugdir, label)
        srcdir    = os.path.join(xcfdir, label)
        filelist  = filelists[label]
        print("Processing {} directory.".format(label))
        aug = ImageAugmentor(srcdir, tgtdir, tgtAnndir, filelist, onlycheckpara)
        if not aug.run():
            status = False
            break
        print("{} directory is processed.".format(label))

    if status==True:
        if onlycheckpara:
            msgBox("The {} directory was successfully checked for parasite data.\nNo errors!".format(xcfdir), gtk.MESSAGE_INFO)
        else:
            print("The augmented PNG files and {} are successfully created in {}".format(LABELFILE, tgtAugdir))
    else:
        if onlycheckpara:
            msgBox("There were errors while checking parasite data. See Gimp output.".format(xcfdir), gtk.MESSAGE_ERROR)
        else:
            msgBox("There were erros during augmentation!".format(LABELFILE, tgtAugdir), gtk.MESSAGE_ERROR)

#
############################################################################
#
register (
    "createAugmented",     # Name registered in Procedure Browser
    "Create augmented images for CNN training (saved as PNG)", # Widget title
    "Create augmented images for CNN training (saved as PNG). Annotations are saved as XML.",
    "Kiran Maheriya",         # Author
    "Kiran Maheriya",         # Copyright Holder
    "May 2016",               # Date
    "3. Create Augmented Images (PNG)", # Menu Entry
    "",     # Image Type
    [
    ( PF_DIRNAME, "srcdir",        "Source Directory Containing Labeled XCF Images:", origDir ),
    ( PF_RADIO,   "onlycheckpara", "Check Parasites or Augment?", 0, (("Augment Images", 0),("Only Check Parasites",1))), # note bool indicates initial setting of buttons
    ],
    [],
    createAugmented,   # Matches to name of function being defined
    menu = "<Image>/DVIA/Dir Ops (Det)"  # Menu Location
    )   # End register

main() 

#   File = roiCreator.py
#   Class to create RoI and scaling the image appropriately.
#
############################################################################
#
from gimpfu import *
import gtk
from dvia_common import msgBox

PREFERRED_ASPECT = 300.0/400.0
class RoiCreator:
    def __init__(self, img, imgmin=600, imgmax=1000, torgb=True):
        '''
        imgmin is the preferred smaller edge size of the target image
        imgmax is the maximum edge size of the target image
        imgmin and imgmax allow a range of aspect ratio selections instead of 
           a fixed aspect ratio -- including landscape and portrait selections
        '''
        self.img        = img
        self.imgmin     = imgmin
        self.imgmax     = imgmax
        self.torgb      = torgb
        
    def doit(self):
        # This function uses current selection as RoI and tries to center it in the image
        # and crops around it leaving upto 50 pixels on each side or RoI (if possible)
    
        ## Convert to RGB if required
        if self.torgb and pdb.gimp_image_base_type(self.img) != 0:  # Not RGB
            try:
                pdb.gimp_image_convert_rgb(self.img)
            except:
                pass

        pdb.gimp_image_resize_to_layers(self.img)
    
        # Check and re-calculate roi selection based on preferences
        (x1,y1, x2,y2) = pdb.gimp_selection_bounds(self.img)[1:]
        # Get the RoI coordinates
        roi_x = x1
        roi_y = y1
        roi_w = x2 - x1
        roi_h = y2 - y1
        # Check for aspect to be within bounds, and adjust only if out of bounds
        im_size_min = min(roi_w, roi_h)
        im_size_max = max(roi_w, roi_h)
        aspect = float(im_size_min)/float(im_size_max)
        ASPECT_MIN = float(self.imgmin)/float(self.imgmax)              # For example, 300/500 = 0.60
        ASPECT_MAX = 1.0 #PREFERRED_ASPECT + (PREFERRED_ASPECT - ASPECT_MIN) # For example, 300/400 + (300/400 - 300/500) = 0.90 
        nh = roi_h
        nw = roi_w
        #print 'aspect={}, ASPECT_MIN={}, ASPECT_MAX={}'.format(aspect, ASPECT_MIN, ASPECT_MAX)
        if (aspect > ASPECT_MAX or aspect < ASPECT_MIN): # Aspect out of bounds. Fix it.
            if (aspect < ASPECT_MIN): # Wider/Narrower selection. Scale down wider/taller dimension
                if nw > nh: # Landscape.  
                    nw   = int(float(roi_h)/(ASPECT_MIN))  # nw reduced
                else:
                    nh   = int(float(roi_w)/(ASPECT_MIN))  # nh reduced
            else:                     # Squarer selection. Scale down smaller dimension
                if nw > nh: # Landscape.  
                    nh   = int(float(roi_w)*(ASPECT_MAX))  # nh reduced
                else:
                    nw   = int(float(roi_h)*(ASPECT_MAX))  # nw reduced
            aspect = float(min(nw,nh))/float(max(nw,nh))
            #print('Aspect out-of-bounds. New aspect calculated: {}'.format(aspect))
        # Now get new selection coordinates.
        # Following tries to move selection without moving a selection edge that touches an image edge
        if x1==0: # Selection touches left edge. Give it preference for x calculation
            roi_x = x1
        elif x2==self.img.width: # Selection touches right edge
            roi_x = x2 - nw
        if y1==0: # Selection touches top edge. Give it preference for y calculation
            roi_y = y1
        elif y2==self.img.height:
            roi_y = y2 - nh
        # Now the n* represent the new bounding box
        pdb.gimp_image_select_rectangle(self.img, 2, roi_x, roi_y, nw, nh)
        roi = pdb.gimp_selection_save(self.img) # roi is a channel
        pdb.gimp_item_set_name(roi, "RoI")      # other scripts can use this as a check for RoI
        pdb.gimp_item_set_visible(roi, TRUE)
        pdb.gimp_image_select_item(self.img, 2, roi) # absolute selection
        pdb.gimp_displays_flush()
        #print("Crop: X:{x}, Y:{y}, W:{w}, H:{h}, new aspect:{a}".format(x=roi_x, y=roi_y, w=nw, h=nh, a=aspect))
        # Crop around RoI
        pdb.gimp_image_resize(self.img, nw, nh, -roi_x, -roi_y)

        pdb.gimp_context_set_interpolation(INTERPOLATION_LANCZOS)
        ## Image rescale (only if required)
        if im_size_min > self.imgmin or im_size_max > self.imgmax: 
            ## This is similar to py-faster-rcnn
            imgscale   = float(self.imgmin)/float(min(nw,nh))  ## Ideal scale
            if (max(nw,nh)*imgscale) > self.imgmax:
                # The normal scaling will cause image max size rule to break. 
                # Change the scale to clamp the max size
                imgscale = float(self.imgmax)/float(max(nw,nh))
            # Now scale the image down
            nw = round(imgscale*nw)
            nh = round(imgscale*nh)
            pdb.gimp_image_scale(self.img, nw, nh)
        
        #print 'New size: w:{}, h:{}'.format(nw,nh)
        pdb.gimp_selection_none(self.img)
        try:
            pdb.gimp_image_set_active_layer(self.img, pdb.gimp_image_get_layer_by_name(self.img, 'base'))
        except:
            pass


#EOF
#   File = roiCreator.py
#   Class to create RoI and scaling the image appropriately.
#
############################################################################
#
from gimpfu import *

class RoiCreator:
    def __init__(self, img, width=300, height=400, torgb=True):
        '''
        '''
        self.img        = img
        self.tgt_width  = width
        self.tgt_height = height
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
    
        # Crop around RoI
        bb  = pdb.gimp_selection_bounds(self.img)
        roi = pdb.gimp_selection_save(self.img) # roi is a channel
        pdb.gimp_item_set_name(roi, "RoI")      # other scripts can use this as a check for RoI
        pdb.gimp_item_set_visible(roi, TRUE)
        pdb.gimp_image_select_item(self.img, 2, roi) # absolute selection
        pdb.gimp_displays_flush()
    
        # Now get the RoI coordinates
        roi_w = bb[3]-bb[1]
        roi_h = bb[4]-bb[2]
        roi_x = bb[1]
        roi_y = bb[2]
        # Crop image down. Clamp to smaller of height or width if selection is not correct aspect
        aspect = float(roi_w)/float(roi_h)
        ASPECT = float(self.tgt_width)/float(self.tgt_height)
        nh = roi_h
        nw = roi_w
        #print 'aspect={}, ASPECT={}'.format(aspect, ASPECT)
        if (aspect > ASPECT+0.002 or aspect < ASPECT-0.002): # Aspect is not correct. User must have selected improperly
            if (aspect > ASPECT): # Wider selection. Scale down wider dimension -- the width
                nw   = int(float(roi_h)*ASPECT)
            else:                 # Taller selection. Scale down taller dimension --  the height
                nh   = int(float(roi_w)*ASPECT)
        #print("Crop stats: X:{x}, Y:{y}, W:{w}, H:{h}, new aspect:{a}".format(x=roi_x, y=roi_y, w=nw, h=nh, a=float(nw)/float(nh)))
        pdb.gimp_image_resize(self.img, nw, nh, -roi_x, -roi_y)
    
        # Now scale the image down to have max of IMG_SIZE_W/H dimension (images smaller than this are left untouched)
        if nw > self.tgt_width or nh > self.tgt_height:
            nw = self.tgt_width
            nh = self.tgt_height
        pdb.gimp_image_scale(self.img, nw, nh)
        pdb.gimp_selection_none(self.img)
        try:
            pdb.gimp_image_set_active_layer(self.img, pdb.gimp_image_get_layer_by_name(self.img, 'group'))
        except:
            pass


#EOF
#!/usr/bin/env python
#
# Currently this script only handles one instance per class per image
# There can be multiple classes per image, but only one instance per class
# Since we will only support multi-label-classification (MLC); but not multi-instancce 
# for DVIA CNN, this is fine.
#
# However, if we decide to support multi-label-multi-instance classification,
#    it is easy enough to add this functionality in the script: Create more 
#    layers per label. One for each instance.

from gimpfu import *
import sys, os
import pickle
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade

scriptpath = os.path.dirname(os.path.realpath( __file__ ))
#scriptrootdir  = os.path.sep.join(scriptpath.split(os.path.sep)[:-4])
sys.stderr = open(os.path.join(os.environ['HOME'], '/tmp/gimpstderr.txt'), 'w')
sys.stdout = open(os.path.join(os.environ['HOME'], '/tmp/gimpstdout.txt'), 'w')

class labelCreator:
    def __init__(self, img):
        self.img = img
        self.grp = pdb.gimp_image_get_layer_by_name(img, 'group')
        pdb.gimp_image_set_active_layer(img, self.grp)

        ## Check image for label data. Create an imaage layer for each label found
        para = img.parasite_find('ldata')
        if para:
            self.ldata = pickle.loads(para.data)
            self.labels = self.ldata['labels']
            self.layers = self.ldata['layers']
        else:
            self.labels = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False, 'badfloor': False, 'drop': False }
            self.layers = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False, 'badfloor': False, 'drop': False }
            self.ldata = {'labels': self.labels, 'layers': self.layers}

        self.nps = {'catchall' : (), 'stair' : (), 'curb' : (), 'doorframe': (), 'badfloor': () }
        self.bbs = {'catchall' : (), 'stair' : (), 'curb' : (), 'doorframe': (), 'badfloor': () }
        self.ldata['NP'] = self.nps
        self.ldata['BB'] = self.bbs

        self.gladefile = os.path.join(scriptpath, "labelCreator.glade") 
        self.wtree = gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        funcmap = {
                "on_cbx_labels_changed"      : self.labelChanged,
                "on_add_label_clicked"       : self.addLabel,
                "on_add_bb_clicked"          : self.addBB,
                "on_add_np_clicked"          : self.addNP,
                "on_delete_label_clicked"    : self.delLabel,
                "on_quit_button_clicked"     : self.quit,
                "on_addLabelsWindow_destroy" : self.quit,
                "on_rbtn_np_toggled"         : self.rbToggled,
        }
        self.wtree.connect_signals(funcmap)

        ## Get all the handles
        self.win = self.wtree.get_object("addLabelsWindow")
        self.btn_addLabel = self.wtree.get_object("add_label")
        self.btn_addBB    = self.wtree.get_object("add_bb")
        self.btn_addNP    = self.wtree.get_object("add_np")
        self.btn_delLabel = self.wtree.get_object("delete_label")
        self.rbtn         = self.wtree.get_object("rbtn_np")
        self.win.show_all()

        self.npsel = True
        ## Hide all the buttons (only combobox active)
        self.enableBBNP = False
        self.btn_addNP.unmap()
        self.btn_addBB.unmap()

        self.btn_addLabel.unmap()
        self.btn_delLabel.unmap()

        self.rbtn.set_active(True)  # Enable NP by default

        gtk.main()

            
    def rbToggled(self, widget):
        if self.rbtn.get_active():
            self.npsel = True
        else:
            self.npsel = False
        self.showButtonsBBNP()
    
    def showButtonsBBNP(self):
        if self.npsel:
            self.btn_addNP.show()
            self.btn_addNP.map()
            if not self.enableBBNP:
                self.btn_addNP.unmap()
            self.btn_addBB.hide()
        else:
            self.btn_addBB.show()
            self.btn_addBB.map()
            if not self.enableBBNP:
                self.btn_addBB.unmap()
            self.btn_addNP.hide()

    def quit(self, widget):
        self.saveParasite()
        try:self.win.destroy()
        except: pass
#         (nb, brushes) = pdb.gimp_brushes_get_list('npstar')
#         for np in brushes:
#             pdb.gimp_brush_delete(np)
        gtk.main_quit()

    def labelChanged(self, cbox):
        '''Called when combobox selection changes
        Task: If label exists make some visual changes: e.g., show label layer
        If BB or NP exists, show that.'''
        cbx_labels = cbox
        cbx_model  = cbx_labels.get_model()
        self.lbl   = cbx_model[cbox.get_active()][0].lower()

        self.enableBBNP = False
        if self.labels[self.lbl]: # label exists
            self.btn_addLabel.unmap()
            self.btn_delLabel.map()
            if self.lbl != 'catchall':
                #self.msgBox('labelChanged: Label is not catchall ({})'.format(self.lbl), gtk.MESSAGE_INFO)
                self.enableBBNP = True
        else: # Label doesn't exist
            self.btn_addLabel.map()
            self.btn_delLabel.unmap()
        self.showButtonsBBNP()

    def addLabel(self, widget):
        '''Add the label as parasite and create a layer for it. If the label already
        exists, only layer needs to be created'''
        self.labels[self.lbl] = True

        self.btn_addLabel.unmap()
        self.btn_delLabel.map()
        if self.lbl == 'catchall':
            #self.msgBox('addLabel: Label is catchall ({})'.format(self.lbl), gtk.MESSAGE_INFO)
            self.enableBBNP = False
        else:
            #self.msgBox('addLabel: Label is not catchall ({})'.format(self.lbl), gtk.MESSAGE_INFO)
            self.enableBBNP = True
        self.showButtonsBBNP()
        self.saveParasite()


    def addBB(self, widget):
        '''Add a bounding polygon in the BB layer and a bounding box in the image parasite
        based on user selection.'''
        if self.lbl == 'catchall' or self.lbl is None:
            self.msgBox('add BB should not be called for label "{}".'.format(self.lbl), gtk.MESSAGE_ERROR)
            return
        bb = pdb.gimp_selection_bounds(self.img)
        if not bb[0]:
            self.msgBox("Make a SELECTION for the bounding box (BB) and click me again.", gtk.MESSAGE_ERROR)
            return

        lname = self.lbl+"_bb"
        lmode = OVERLAY_MODE
        lyr = self.createLayer(lname, lmode, newlayer=True)

        pdb.gimp_context_set_background('#202020')
        pdb.gimp_edit_bucket_fill(self.img.active_drawable, BG_BUCKET_FILL, NORMAL_MODE, 100, 0, FALSE, 0, 0)

        pdb.gimp_image_select_item(self.img, CHANNEL_OP_REPLACE, lyr)
        # Get new bounding box
        bb = pdb.gimp_selection_bounds(self.img)
        self.bbs[self.lbl] = bb[1:]
        pdb.gimp_selection_none(self.img)
        pdb.gimp_displays_flush()
        self.saveParasite()

    def addNP(self, widget):
        '''Add the nearest point based on user selection. A square is adeded in the image and NP is stored as
        a part of the ldata parasite in the image
        '''
        if self.lbl == 'catchall' or self.lbl is None:
            self.msgBox('add NP should not be called for label "{}".'.format(self.lbl), gtk.MESSAGE_ERROR)
            return
        bb = pdb.gimp_selection_bounds(self.img)
        if not bb[0]:
            self.msgBox("Make a SELECTION for the nearest point (NP) and click me again. Bottom-center of the selection will be the nearest point", gtk.MESSAGE_ERROR)
            return

        lname = self.lbl+"_np"
        lmode = NORMAL_MODE
        lyr = self.createLayer(lname, lmode, newlayer=True)

        bb = bb[1:]
        # Find the bottom-center of the bounding box
        x = bb[0] + (bb[2]-bb[0])/2
        y = bb[3]
        self.nps[self.lbl] = (x, y)
        gimp.set_foreground('#ffffff')
        #pdb.gimp_image_select_rectangle(self.img, CHANNEL_OP_REPLACE, x-5, y-10, 10, 10)
        pdb.gimp_image_select_ellipse  (self.img, CHANNEL_OP_REPLACE, x-5, y-10, 10, 10)
        pdb.gimp_edit_bucket_fill(self.img.active_drawable, FG_BUCKET_FILL, NORMAL_MODE, 100, 0, FALSE, 0, 0)

        pdb.gimp_selection_none(self.img)
        pdb.gimp_displays_flush()
        self.saveParasite()

    def delLabel(self, widget):
        # delete BB, NP and the label if they exist.
        self.labels[self.lbl] = False
        self.layers[self.lbl] = False
        self.nps[self.lbl] = ()
        self.bbs[self.lbl] = ()
        lyr = pdb.gimp_image_get_layer_by_name(self.img, self.lbl+"_np")
        if lyr: # Layer exists. delete it.
            pdb.gimp_image_remove_layer(self.img, lyr)
        lyr = pdb.gimp_image_get_layer_by_name(self.img, self.lbl+"_bb")
        if lyr: # Layer exists. delete it.
            pdb.gimp_image_remove_layer(self.img, lyr)

        self.btn_delLabel.unmap()
        self.btn_addLabel.map()
        self.enableBBNP = False
        self.showButtonsBBNP()

        pdb.gimp_displays_flush()
        self.saveParasite()

    def msgBox(self, msg, btype):
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
        msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
        msgBox.run()
        msgBox.destroy()

    def saveParasite(self):
        try: self.img.attach_new_parasite('ldata', 5, pickle.dumps(self.ldata))
        except:
            pdb.gimp_message("Could not save ldata parasite") 

    def createLayer(self, lname, lmode, newlayer=False):
        lyr = pdb.gimp_image_get_layer_by_name(self.img, lname)
        if lyr and newlayer:
            pdb.gimp_image_remove_layer(self.img, lyr)
            lyr = None
        if not lyr: # Layer doesn't exist. Add it.
            lyr = pdb.gimp_layer_new(self.img, self.img.width, self.img.height, RGBA_IMAGE, lname, 100, lmode)
            pdb.gimp_image_insert_layer(self.img, lyr, self.grp, -1)

        self.layers[self.lbl] = True
        pdb.gimp_image_set_active_layer(self.img, lyr)
        pdb.gimp_item_set_visible(lyr, TRUE)
        return lyr


if __name__ == "__main__":
    try:
        a = labelCreator(None)
    except KeyboardInterrupt:
        pass

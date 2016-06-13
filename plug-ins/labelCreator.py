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
import os
import pickle
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
from gtk import gdk
from pprint import pprint

from dvia_common import *
from roiCreator import RoiCreator

scriptpath = os.path.dirname(os.path.realpath( __file__ ))

IMG_SIZE_W = 300
IMG_SIZE_H = 400
USE_NP_VISUAL_GRADIENT = True  # Use gradient to visualize NP?
USE_BB_VISUAL_BORDER   = True  # Use a border in addition to solid overlay for bounding box?

class LabelCreator:
    def __init__(self, img_or_imgdir, single=True):
        self.single = single
        self.classes     = dvia_classes
        self.bordercolors = dvia_bordercolors
        self.classids = {}
        self.iconTexts = {}
        self.iconImages = {}
        clsid = 0
        for cls in self.classes:
            self.classids[cls] = clsid
            self.iconTexts[cls] = '{}_{}'.format(clsid, cls)
            self.iconImages[cls] = 'icons/{}_{}.png'.format(clsid, cls)
            clsid += 1

        if not self.single:
            self.srcdir    = img_or_imgdir
            self.srcfiles = []
            for fname in os.listdir(self.srcdir):
                if not fname.lower().endswith('.xcf'):
                    continue # skip non-xcf files
                self.srcfiles.append(fname)
            # Find all of the xcf files in the list
            if len(self.srcfiles) == 0:
                self.msgBox("Source directory {} didn't contain any XCF images.".format(self.srcdir), gtk.MESSAGE_ERROR)
                return
            self.srcfiles.sort()
            self.endqueue = len(self.srcfiles) - 1
            self.index = 0
            self.openImage()
        else:
            self.img = img_or_imgdir
            self.setupSingleImage()

        self.gladefile = os.path.join(scriptpath, "labelCreator.glade") 
        self.wtree = gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        funcmap = {
                "on_add_roi_clicked"         : self.addRoI,
                "on_add_label_clicked"       : self.addLabel,
                "on_add_bb_clicked"          : self.addBB,
                "on_add_np_clicked"          : self.addNP,
                "on_del_label_clicked"       : self.delLabel,
                "on_del_bb_clicked"          : self.delBB,
                "on_del_np_clicked"          : self.delNP,
                "on_prev_button_clicked"     : self.prev,
                "on_next_button_clicked"     : self.next,
                "on_quit_button_clicked"     : self.quit,
                "on_addLabelsWindow_destroy" : self.quit,
        }
        self.wtree.connect_signals(funcmap)

        # # Get all the handles
        self.win          = self.wtree.get_object("addLabelsWindow")
        self.bx_main      = self.wtree.get_object("box_main")
        self.btn_addRoI   = self.wtree.get_object("add_roi")
        self.btn_addLabel = self.wtree.get_object("add_label")
        self.btn_addBB    = self.wtree.get_object("add_bb")
        self.btn_addNP    = self.wtree.get_object("add_np")
        self.btn_delLabel = self.wtree.get_object("del_label")
        # new
        self.btn_prev     = self.wtree.get_object("prev_button")
        self.btn_next     = self.wtree.get_object("next_button")
        self.btn_delNP    = self.wtree.get_object("del_np")
        self.btn_delBB    = self.wtree.get_object("del_bb")
        #
        self.bx_np_bb_add = self.wtree.get_object("bx_np_bb_add")
        self.bx_np_bb_del = self.wtree.get_object("bx_np_bb_del")
        self.initIconView(self.wtree)
        self.win.show_all()
        ## Hide next/prev in single image mode
        if self.single:
            self.btn_prev.hide()
            self.btn_next.hide()

        self.updateLayout()
        gtk.main()

    def addRoI(self, widget):
        bb = pdb.gimp_selection_bounds(self.img)
        if not bb[0]:
            self.msgBox("Mark a selection for the RoI and call me again.", gtk.MESSAGE_ERROR)
            return
        roi = RoiCreator(self.img, IMG_SIZE_W, IMG_SIZE_H, torgb=True)
        roi.doit()
        self.saveImage()
        self.setupSingleImage()
        self.updateLayout()

    def setupSingleImage(self):
        self.grp = pdb.gimp_image_get_layer_by_name(self.img, 'group')
        pdb.gimp_image_set_active_layer(self.img, self.grp)
        ch = pdb.gimp_image_get_channel_by_name(self.img, 'RoI')
        if ch is not None:
            self.hasRoI = True
        else:
            self.hasRoI = False
        # # Check image for label data. Create an image layer for each label found
        para = self.img.parasite_find('ldata')
        if para:
            self.ldata = pickle.loads(para.data)
            self.labels = self.ldata['labels']
            self.layers = self.ldata['layers']
        else:
            self.labels = dict(dvia_labels)
            self.layers = dict(dvia_layers)
            self.ldata = dict(dvia_ldata)

        self.objects  = self.ldata['objects']

        self.lbl = ''
        # Find first available label (if any)
        for lbl in self.classes:
            if self.labels[lbl]:
                self.lbl = lbl
                break
        #print('Objects: ')
        #pprint(self.objects)

    def updateLayout(self):
        if not self.hasRoI:
            self.bx_main.unmap()
            self.btn_addRoI.show()
            return

        self.bx_main.map()
        self.btn_addRoI.hide()
        # This should be called immediately after opening an image and reading parasite data
        self.updateIconView()
        if self.lbl != '' and self.labels[self.lbl]: # Label exists
            # Show Del label button
            self.showButtonsBBNP()
            self.showButtonDelLabel()
        else:
            # # Hide all the buttons
            self.bx_np_bb_add.unmap()
            self.bx_np_bb_del.unmap()
    
            self.btn_addLabel.show()
            self.btn_addLabel.unmap()
            self.btn_delLabel.hide()

    def showButtonsBBNP(self):
        self.btn_delNP.set_label('Delete NPs for "{}"'.format(self.lbl))
        self.btn_delBB.set_label('Delete BBs for "{}"'.format(self.lbl))
        self.bx_np_bb_add.map()
        self.bx_np_bb_del.map()

    def hideButtonsBBNP(self):
        self.bx_np_bb_add.unmap()
        self.bx_np_bb_del.unmap()

    def showButtonAddLabel(self):
        self.btn_addLabel.set_label('Add Label "{}"'.format(self.lbl))
        self.btn_addLabel.show()
        self.btn_addLabel.map()
        self.btn_delLabel.hide()

    def showButtonDelLabel(self):
        self.btn_delLabel.set_label('Delete Label "{}"'.format(self.lbl))
        self.btn_addLabel.hide()
        self.btn_delLabel.show()
        self.btn_delLabel.map()

    def quit(self, widget):
        #self.saveParasite()
        if not self.single:
            self.closeImage()
        try:self.win.destroy()
        except: pass
        gtk.main_quit()

    def next(self, widget):
        if self.index>=self.endqueue:
            self.msgBox("This is the last file. No more files in this direction.", gtk.MESSAGE_INFO)
            return
        self.closeImage()
        self.index += 1
        self.openImage()
        self.updateLayout()

    def prev(self, widget):
        if self.index<=0:
            self.msgBox("This is the first file. No more files in this direction.", gtk.MESSAGE_INFO)
            return
        self.closeImage()
        self.index -= 1
        self.openImage()
        self.updateLayout()

    def openImage(self):
        self.srcfile = os.path.join(self.srcdir, self.srcfiles[self.index])
        print 'Opening {}'.format(self.srcfile)
        self.img  = pdb.gimp_file_load(self.srcfile, self.srcfile)
        self.disp = pdb.gimp_display_new(self.img)
        self.setupSingleImage()
        
    def closeImage(self):
        if len(gimp.image_list()) == 0 or self.img is None:
            return
        pdb.gimp_image_clean_all(self.img)
        pdb.gimp_display_delete(self.disp)
        self.img = None

    def saveImage(self):
        if len(gimp.image_list()) == 0 or self.img is None:
            return
        self.saveParasite()
        if self.img.filename is None:
            self.msgBox('Image ({}) does not have filename embedded'.format(self.srcfile), gtk.MESSAGE_ERROR)
        pdb.gimp_xcf_save(0, self.img, self.img.active_drawable, self.img.filename, self.img.filename)
        pdb.gimp_image_clean_all(self.img)

    def labelChanged(self, lbl):
        '''Called when iconview selection changes
        TODO: If label exists, make some visual changes: e.g., show label layer
        If BB or NP exists, show that.'''
        self.lbl = lbl

        if self.labels[self.lbl]: # label exists
            self.showButtonDelLabel()
            if self.lbl == 'catchall':
                self.hideButtonsBBNP()
            else:
                self.showButtonsBBNP()
        else: # Label doesn't exist
            self.showButtonAddLabel()
            self.hideButtonsBBNP()

    def addLabel(self, widget):
        '''Add the label as parasite and create a layer for it. If the label already
        exists, only layer needs to be created'''
        self.labels[self.lbl] = True

        self.showButtonDelLabel()
        if self.lbl == 'catchall':
            self.hideButtonsBBNP()
        else:
            self.showButtonsBBNP()
        
        self.saveImage()


    def addBB(self, widget):
        '''
        Add a bounding polygon in the BB layer and a bounding box in the image parasite
        based on user selection.
        addBB adds an object to objects parasite (addNP doesn't)
        '''
        if self.lbl == 'catchall' or self.lbl is None:
            self.msgBox('add BB should not be called for label "{}".'.format(self.lbl), gtk.MESSAGE_ERROR)
            return
        bbrct = pdb.gimp_selection_bounds(self.img)
        if not bbrct[0]:
            self.msgBox("Make a SELECTION for the bounding box (BB) and click me again.", gtk.MESSAGE_ERROR)
            return

        #print 'In addBB. Length of self.objects["{}"]={}'.format(self.lbl, len(self.objects[self.lbl]))
        index = len(self.objects[self.lbl])
        lname = "{lbl}_bb{idx:d}".format(lbl=self.lbl,idx=index)
        #print '          Adding {}, index {}'.format(lname, index)
        lyr  = self.createLayer(lname, NORMAL_MODE, newlayer=True)
        bb   = createBBVisual(self.img, lyr, self.lbl, USE_BB_VISUAL_BORDER)
        obj  = dict(dvia_object)
        obj['bb']      = bb
        obj['bbLayer'] = lyr.name
        obj['index']   = index
        self.objects[self.lbl].append(obj)
        self.saveImage()

    def addNP(self, widget):
        '''
        Add the nearest point based on user selection. A shape is added in the image and NP is stored.
        NP requires an existing BB. We search for surrounding BB to find the object in which to add the new NP.
        This is the only robust way to allow multiple instances of BBs and NPs without user errors.
        addBB adds an object to objects parasite (addNP doesn't)
        '''
        if self.lbl == 'catchall' or self.lbl is None:
            self.msgBox('add NP should not be called for label "{}".'.format(self.lbl), gtk.MESSAGE_ERROR)
            return
        bbrct = pdb.gimp_selection_bounds(self.img)
        if not bbrct[0]:
            self.msgBox("Make a SELECTION for the nearest point (NP) and click me again. Bottom-center of the selection will be the nearest point", gtk.MESSAGE_ERROR)
            return

        ## Get surrounding object so that we can insert NP in it.
        x1,y1, x2,y2 = bbrct[1:]
        # Find the bottom-center of the bounding box
        xc = x1 + (x2-x1)/2
        obj = self.findSurroundingObject(self.lbl, (xc, y2))
        if obj is None:
            self.msgBox("Couldn't find surrounding BB for this NP for label {}.".format(self.lbl), gtk.MESSAGE_ERROR)
            return
        #print 'In addNP. Length of self.objects["{}"]={}'.format(self.lbl, len(self.objects[self.lbl]))
        if obj['npLayer']:
            pdb.gimp_image_remove_layer(self.img, obj['npLayer'])
            obj['npLayer'] = None
        lname = "{lbl}_np{idx:d}".format(lbl=self.lbl,idx=obj['index'])
        #print '          Adding {}, index {}'.format(lname, obj['index'])
        lyr = self.createLayer(lname, NORMAL_MODE, newlayer=True)

        np = createNPVisual(self.img, lyr, self.lbl, USE_NP_VISUAL_GRADIENT)
        obj['np'] = np
        obj['npLayer'] = lyr.name
        self.saveImage()

    def delLabel(self, widget):
        # delete BB, NP and the label if they exist.
        self.delBB(None)
        self.labels[self.lbl] = False
        self.layers[self.lbl] = False
        
        self.showButtonAddLabel()
        self.hideButtonsBBNP()

        pdb.gimp_displays_flush()
        self.saveImage()

    def delBB(self, widget):
        # delete BBs of _current_ label if they exist.
        #print 'In delBB. Length of self.objects["{}"]={}'.format(self.lbl, len(self.objects[self.lbl]))
        for obj in self.objects[self.lbl]:
            if obj['bbLayer']:
                #print '   Deleting {}'.format(obj['bbLayer'])
                lyr = pdb.gimp_image_get_layer_by_name(self.img, obj['bbLayer'])
                if lyr: 
                    pdb.gimp_image_remove_layer(self.img, lyr)
                obj['bbLayer'] = None
        # When BBs are deleted, NPs cannot exist; must be deleted as well
        self.delNP(None)

        self.objects[self.lbl] = []
        pdb.gimp_displays_flush()
        self.saveImage()

    def delNP(self, widget):
        # delete NPs of current label if they exist.
        #print 'In delNP. Length of self.objects["{}"]={}'.format(self.lbl, len(self.objects[self.lbl]))
        for obj in self.objects[self.lbl]:
            obj['np'] = []
            if obj['npLayer']:
                #print '   Deleting {}'.format(obj['npLayer'])
                lyr = pdb.gimp_image_get_layer_by_name(self.img, obj['npLayer'])
                if lyr:
                    pdb.gimp_image_remove_layer(self.img, lyr)
                obj['npLayer'] = None

        pdb.gimp_displays_flush()
        self.saveImage()

    def msgBox(self, msg, btype):
        flag = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
        msgBox = gtk.MessageDialog(None, flag, btype, gtk.BUTTONS_OK, msg)
        msgBox.run()
        msgBox.destroy()

    def saveParasite(self):
        if self.img is None:
            return
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

    def findSurroundingObject(self, lbl, np):
        '''
        For a given lbl and bb, finds surrounding object using BB
        Returns pointer to object within the objects[lbl] array.
        Returns None if obj with appropriate BB is not found.
        '''
        npx,npy = np
        if len(self.objects[lbl])==0:
            print "  There are no objects created for for this label. Returning None."
            return None
        for iobj in xrange(len(self.objects[lbl])):
            obj = self.objects[lbl][iobj]
            if len(obj['bb']) == 0:
                print 'Found object, but there is no BB. Returning None.'
                return None 
            x1,y1,x2,y2 = obj['bb']
            if (x1 <= npx and npx <= x2) and (y1 <= npy and npy <= y2):
                return obj
        return None


    # Iconview for label/class selection
    def initIconView(self, wtree):
        self.store = self.create_store()
        self.fill_store()
        sw = wtree.get_object("labels_window")

        iconView = gtk.IconView(self.store)
        iconView.set_selection_mode(gtk.SELECTION_SINGLE)
        iconView.set_text_column(0)
        iconView.set_pixbuf_column(1)

        iconView.connect("selection-changed", self.iconSelectionChanged)
        sw.add(iconView)
        iconView.grab_focus()
        self.icon_view = iconView

    def create_store(self):
        store = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
        store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        return store
    
    def fill_store(self):
        self.store.clear()
        for lbl in self.classes:
            icon = gtk.Image()
            icon.set_from_file(os.path.join(scriptpath, self.iconImages[lbl]))
            self.store.append([self.iconTexts[lbl], icon.get_pixbuf(), lbl])

    def iconSelectionChanged(self, iview):
        model = iview.get_model()
        if len(iview.get_selected_items())>0:
            item = iview.get_selected_items()[0][0]
            lbl = model[item][2].lower()
            #print "Icon selection changed to {}.".format(lbl)
            self.labelChanged(lbl)

    def updateIconView(self):
        if self.lbl == '':
            self.icon_view.unselect_all()
        else:
            self.icon_view.select_path(self.classids[self.lbl])


#EOF
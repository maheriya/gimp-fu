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

import dvia_common as dv
from dvia_common import *
from roiCreator import RoiCreator

scriptpath = os.path.dirname(os.path.realpath( __file__ ))

IMG_SIZE_MIN = 300
IMG_SIZE_MAX = 500
USE_NP_VISUAL_GRADIENT = True  # Use gradient to visualize NP?
USE_BB_VISUAL_BORDER   = True  # Use a border in addition to solid overlay for bounding box?

class LabelCreator:
    def __init__(self, img_or_imgdir, single=True):
        self.single  = single
        self.classes = dvia_classes
        self.bordercolors = dvia_bordercolors
        self.classids = {}
        self.iconTexts = {}
        self.iconImages = {}
        self.slider = None
        clsid = 0

        if self.single:
            self.img        = img_or_imgdir
            self.srcdir     = os.path.dirname(self.img.filename)
        else:
            self.img        = None
            self.srcdir     = img_or_imgdir
        ## Look for DB file and use it to bootstrap if it exists
        self.dbfilename = os.path.join(self.srcdir, dv.DBFILENAME)
        self.flagsdb = {}
        if os.path.exists(self.dbfilename):
            with open(self.dbfilename, 'r') as f:
                self.flagsdb = pickle.load(f)
            dbexists = True
            f.close()
        else:
            dbexists = False
            
        if not 'ROI' in self.flagsdb:
            self.flagsdb['ROI']   = {}  # For each image, True: RoI exists; False: RoI doesn't exist
            self.flagsdb['LDATA'] = {}  # For each image, ldata (dvia_ldata format)
            self.flagsdb['currFile']  = None       # current working image file name
            self.flagsdb['indexFilename'] = 0      # current index based on Filename sort.
            self.flagsdb['indexRoI']      = 0      # current index based on RoI sort.
            self.flagsdb['currSort']  = 'Filename'
        self.dbIsOpen = True

        for cls in self.classes:
            self.classids[cls] = clsid
            self.iconTexts[cls] = '{}_{}'.format(clsid, cls)
            self.iconImages[cls] = 'icons/{}_{}.png'.format(clsid, cls)
            clsid += 1

        if not self.single:
            self.srcfiles = []
            for fname in os.listdir(self.srcdir):
                if not fname.lower().endswith('.xcf'):
                    continue # skip non-xcf files
                self.srcfiles.append(fname)
            # Find all of the xcf files in the list
            if len(self.srcfiles) == 0:
                self.msgBox("Source directory {} didn't contain any XCF images.".format(self.srcdir), gtk.MESSAGE_ERROR)
                return
            self.srcfiles_sorted = list(self.srcfiles)
            self.srcfiles_sorted.sort()  # Keep filename based srcfiles for easy switching
            ## In case the DB doesn't exist, we need to build it:
            if not dbexists:
                self.updateDBFromScratch()
            self.sortSrcFiles(self.flagsdb['currSort'])
            self.numfiles = len(self.srcfiles)
            self.endqueue = len(self.srcfiles) - 1
            self.sliderChanged = False # To indicate change of index by user via slider
            self.updateSlider  = True  # To indicate that slider should be updated due to next/prev button presses
            self.openImage()

        self.setupGUI()
        self.setupSingleImage()
        self.initIconView(self.wtree)
        self.win.show_all()
        ## Hide next/prev in single image mode
        if self.single:
            self.btn_prev.hide()
            self.btn_next.hide()
            self.slider.hide()
        self.updateLayout()
        gtk.main()

    def setupGUI(self):
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
                "on_sortfilename_button_clicked": self.sortOnFilename,
                "on_sortroi_button_clicked"  : self.sortOnRoI,
                "on_addLabelsWindow_destroy" : self.quit,
                "on_slider_value_changed"    : self.indexChanged,
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
        self.slider       = self.wtree.get_object("slider")
        self.slider_adj   = self.wtree.get_object("slider_adj")
        self.btn_delNP    = self.wtree.get_object("del_np")
        self.btn_delBB    = self.wtree.get_object("del_bb")
        #
        self.lbl_imgname  = self.wtree.get_object("imgname_label")
        self.bx_np_bb_add = self.wtree.get_object("bx_np_bb_add")
        self.bx_np_bb_del = self.wtree.get_object("bx_np_bb_del")
        if not self.single:
            self.slider_adj.upper = self.numfiles


    def addRoI(self, widget):
        bb = pdb.gimp_selection_bounds(self.img)
        if not bb[0]:
            ## Assume that the user wants the whole image to be selected
            pdb.gimp_selection_all(self.img)
            bb = pdb.gimp_selection_bounds(self.img)
            #self.msgBox("Mark a selection for the RoI and call me again.", gtk.MESSAGE_ERROR)
            #return
        roi = RoiCreator(self.img, IMG_SIZE_MIN, IMG_SIZE_MAX, torgb=True)
        roi.doit()
        self.flagsdb['ROI'][self.srcfile] = True
        self.saveImage()
        self.setupSingleImage()
        self.updateLayout()

    def setupSingleImage(self):
        self.grp = pdb.gimp_image_get_layer_by_name(self.img, 'group')
        pdb.gimp_image_set_active_layer(self.img, pdb.gimp_image_get_layer_by_name(self.img, 'base'))
        ch = pdb.gimp_image_get_channel_by_name(self.img, 'RoI')
        if ch is not None:
            self.hasRoI = True
        else:
            self.hasRoI = False
        self.flagsdb['ROI'][self.srcfile] = self.hasRoI
        # # Check image for label data. Create an image layer for each label found
        para = self.img.parasite_find('ldata')
        if para:
            self.ldata = pickle.loads(para.data)
            self.labels = self.ldata['labels']
            self.layers = self.ldata['layers']
        else:
            self.labels = dict(dvia_labels)
            self.layers = dict(dvia_layers)
            self.ldata  = dict(dvia_ldata)

        self.objects  = self.ldata['objects']
        ## Update DB
        self.flagsdb['LDATA'][self.srcfile] = dict(self.ldata)
        self.updateDBIndex()
        if self.slider is not None:
            self.slider.set_value(self.index+1) # Update slider

        self.lbl = ''
        # Find first available label (if any)
        for lbl in self.classes:
            if self.labels[lbl]:
                self.lbl = lbl
                break

    def updateLayout(self):
        if not self.single:
            self.lbl_imgname.set_text(self.srcfiles[self.index])
        if not self.hasRoI:
            self.bx_main.hide()
            self.btn_addRoI.show()
            return

        self.bx_main.show()
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
        if not self.single:
            self.closeImage()
        if self.dbIsOpen:
            self.saveDB()
            self.dbIsOpen = False
        try   : self.win.destroy()
        except: pass
        gtk.main_quit()

    def next(self, widget):
        if not self.sliderChanged and self.index>=self.endqueue:
            self.msgBox("This is the last file. No more files in this direction.", gtk.MESSAGE_INFO)
            return
        self.closeImage()
        self.updateSlider = True
        if self.sliderChanged:
            self.sliderChanged = False
        else:
            self.index += 1
            self.slider.set_value(self.index+1) # Update slider
        self.openImage()
        self.updateLayout()

    def prev(self, widget):
        if not self.sliderChanged and self.index<=0:
            self.msgBox("This is the first file. No more files in this direction.", gtk.MESSAGE_INFO)
            return
        self.closeImage()
        self.updateSlider = True
        if self.sliderChanged:
            self.sliderChanged = False
        else:
            self.index -= 1
            self.slider.set_value(self.index+1) # Update slider
        self.openImage()
        self.updateLayout()

    def openImage(self):
        self.srcfile = self.srcfiles[self.index]
        self.srcfullpath = os.path.join(self.srcdir, self.srcfile)
        print 'Opening {}'.format(self.srcfile)
        self.img  = pdb.gimp_file_load(self.srcfullpath, self.srcfullpath)
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

    def indexChanged(self, widget):
        self.slider.set_restrict_to_fill_level(False)
        self.slider.set_fill_level(self.slider.get_value())
        self.slider.set_show_fill_level(True)
        if self.updateSlider:
            self.updateSlider = False
            return
        self.index = int(self.slider.get_value()) - 1
        self.sliderChanged = True
        #print 'Slider Changed to {}'.format(self.index+1)


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
            lyr = pdb.gimp_image_get_layer_by_name(self.img, obj['npLayer'])
            if lyr:
                pdb.gimp_image_remove_layer(self.img, lyr)
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

    def saveDB(self):
        try: dbfile = open(self.dbfilename, 'w')
        except:
            print('Could not open DB file {}'.format(self.dbfilename))
            dv.msgBox('Could not open DB file {}'.format(self.dbfilename), gtk.MESSAGE_ERROR)
            raise
        pickle.dump(self.flagsdb, dbfile)
        dbfile.close()

    def updateDBIndex(self):
        if self.flagsdb['currSort'] == 'Filename':
            self.flagsdb['indexFilename'] = self.index
        elif self.flagsdb['currSort'] == 'RoI':
            self.flagsdb['indexRoI']      = self.index

    def getDBIndex(self):
        if self.flagsdb['currSort'] == 'Filename':
            return self.flagsdb['indexFilename']
        elif self.flagsdb['currSort'] == 'RoI':
            return self.flagsdb['indexRoI']

    def sortSrcFiles(self, stype='Filename'):
        '''
        Implement custom sort here
        '''
        if stype == 'Filename':
            self.sortOnFilename()
        elif stype == 'RoI':
            self.sortOnRoI()

    def sortOnFilename(self, widget=None):
        self.flagsdb['currSort'] = 'Filename'
        self.srcfiles = self.srcfiles_sorted
        self.index    = self.getDBIndex()
        if widget is not None:
            self.closeImage()
            self.updateSlider = True
            self.slider.set_value(self.index+1) # Update slider
            self.openImage()
            self.updateLayout()

    def sortOnRoI(self, widget=None):
        self.flagsdb['currSort'] = 'RoI'
        self.roiImages = [img for img in self.srcfiles_sorted if self.flagsdb['ROI'][img]]
        self.roiImages.sort()
        nonRoiImages = [img for img in self.srcfiles_sorted if not self.flagsdb['ROI'][img]]
        nonRoiImages.sort()
        self.srcfiles = self.roiImages + nonRoiImages
        self.index = len(self.roiImages) # Go to the first nonRoI image
        if self.index == self.numfiles:
            self.index -= 1
        self.updateDBIndex()
        #print("Number of RoI images = {n}. Index = {i}".format(n=len(self.roiImages), i=self.index))
        #print("self.roiImages : {}".format(self.roiImages))
        #print("self.srcfiles sorted on Filename: {}".format(self.srcfiles_sorted))
        #print("self.srcfiles sorted on RoI: {}".format(self.srcfiles))
        if widget is not None:
            self.closeImage()
            self.updateSlider = True
            self.slider.set_value(self.index+1) # Update slider
            self.openImage()
            self.updateLayout()

    def updateDBFromScratch(self):
        self.index = 0
        for f in self.srcfiles_sorted:
            self.updateSlider = False
            self.openImage()
            self.index += 1
            self.closeImage()


#EOF
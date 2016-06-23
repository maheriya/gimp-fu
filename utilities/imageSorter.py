#!/usr/bin/env python
#
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GdkPixbuf

import matplotlib.pyplot as plt
import matplotlib.image as mpimg


scriptpath = os.path.dirname(os.path.realpath( "dummy" ))
## DVIA Common definitions
##
## Empty definitions for labels, layers and NP/BB
dvia_classes      = ('catchall', 'stair', 'curb', 'doorframe')
dvia_cls_ids      = {'stair' : 0, 'curb' : 1, 'doorframe': 2}  ## catchall should be ignored -- this should only be used for MLC format

dvia_bordercolors = {'catchall': '#ffffff', 'stair': '#b80c48', 'curb': '#09b853', 'doorframe': '#0c84b8'}
dvia_labels       = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False} #, 'badfloor': False, 'drop': False }
dvia_layers       = {'catchall' : False, 'stair' : False, 'curb' : False, 'doorframe': False} #, 'badfloor': False, 'drop': False }

# Objects: Per class array of objects which are dict of arrays or nps and bbs
dvia_objects = {'catchall' : [], 'stair' : [], 'curb' : [], 'doorframe': []}
# Object: Each object contains one np, and one bb. Also used to store other object specific info.
dvia_object  = {'np': (), 'bb': (), 'npLayer': None, 'bbLayer': None, 'index': None} ##, 'pose': 'front'}

dvia_ldata =  {'labels': dvia_labels, 'layers': dvia_layers, 'objects': dvia_objects}

## Common function definitions
def msgBox(message, typ=Gtk.MessageType.INFO):
    mBox = Gtk.MessageDialog(parent=None, flags=0, message_type=typ, buttons=Gtk.ButtonsType.OK, text=message)
    mBox.run()
    mBox.destroy()

def questionBox(msg):
    mtype=Gtk.MessageType.QUESTION
    msgBox = Gtk.MessageDialog(parent=None, flags=0, message_type=mtype, buttons=Gtk.ButtonsType.YES_NO, text=msg)
    resp = msgBox.run()
    msgBox.destroy()
    return resp

# msgBox("Hello World!")
# Gtk.main()

USE_LABEL_SELECTOR = False
class ImageSorter:
    def __init__(self, imgdir):
        self.classes = dvia_classes
        self.classids = {}
        self.iconTexts = {}
        self.iconImages = {}
        clsid = 0
        for cls in self.classes:
            self.classids[cls] = clsid
            self.iconTexts[cls] = '{}_{}'.format(clsid, cls)
            self.iconImages[cls] = 'icons/{}_{}.png'.format(clsid, cls)
            clsid += 1

        self.srcdir    = imgdir
        self.srcfiles = []
        for fname in os.listdir(self.srcdir):
            #if not fname.lower().endswith('.xcf'):
            #    continue
            self.srcfiles.append(fname)
        # Find all of the xcf files in the list
        if len(self.srcfiles) == 0:
            self.msgBox("Source directory {} didn't contain any images.".format(self.srcdir), Gtk.MessageType.ERROR)
            return
        self.numfiles = len(self.srcfiles)
        self.srcfiles.sort()
        self.endqueue = len(self.srcfiles) - 1
        self.index = 0
        self.sliderChanged = False # To indicate change of index by user via slider
        self.updateSlider  = False # To indicate that slider should be updated due to next/prev button presses
        self.openImage()

        self.gladefile = os.path.join(scriptpath, "imageSorter.glade")
        self.wtree = Gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        funcmap = {
                "on_add_label_clicked"       : self.addLabel,
                "on_del_label_clicked"       : self.delLabel,
                "on_prev_button_clicked"     : self.prev,
                "on_next_button_clicked"     : self.next,
                "on_quit_button_clicked"     : self.quit,
                "on_mark_good_clicked"       : self.markGood,
                "on_mark_bad_clicked"        : self.markBad,
                "on_addLabelsWindow_destroy" : self.quit,
                "on_slider_value_changed"    : self.indexChanged,
        }
        self.wtree.connect_signals(funcmap)

        # # Get all the handles
        self.win          = self.wtree.get_object("addLabelsWindow")
        self.bx_main      = self.wtree.get_object("box_main")
        self.bx_sel_label = self.wtree.get_object("bx_sel_label")
        self.btn_addLabel = self.wtree.get_object("add_label")
        self.btn_delLabel = self.wtree.get_object("del_label")
        self.btn_good     = self.wtree.get_object("mark_good")
        self.btn_bad    = self.wtree.get_object("mark_bad")
        # new
        self.btn_prev     = self.wtree.get_object("prev_button")
        self.btn_next     = self.wtree.get_object("next_button")
        self.slider       = self.wtree.get_object("slider")
        self.slider_adj   = self.wtree.get_object("slider_adj")
        #
        self.lbl_imgname  = self.wtree.get_object("imgname_label")
        self.initIconView(self.wtree)
        self.win.show_all()

        self.slider_adj.upper = self.numfiles

        self.updateLayout()
        Gtk.main()

    def addRoI(self, widget):
        pass

    def setupSingleImage(self):
        self.lbl = ''
        self.good = True
        self.labels = dict(dvia_labels)
        self.layers = dict(dvia_layers)
        self.ldata = dict(dvia_ldata)

        # Find first available label (if any)
        for lbl in self.classes:
            if self.labels[lbl]:
                self.lbl = lbl
                break

    def updateLayout(self):
        if not USE_LABEL_SELECTOR:
            # hide the label selection and add/del buttons. We are not using that for now
            self.bx_sel_label.hide()

        self.lbl_imgname.set_text(self.srcfiles[self.index])
        self.bx_main.show()
        # This should be called immediately after opening an image and reading parasite data
        if USE_LABEL_SELECTOR:
            self.updateIconView()
            if self.lbl != '' and self.labels[self.lbl]: # Label exists
                # Show Del label button
                self.showButtonDelLabel()
            else:
                self.btn_addLabel.show()
                self.btn_addLabel.unmap()
                self.btn_delLabel.hide()

        self.showButtonsGoodBad()

    def showButtonsGoodBad(self):
        if self.good:
            self.btn_bad.show()
            self.btn_bad.map()
            self.btn_good.hide()
        else:
            self.btn_good.show()
            self.btn_good.map()
            self.btn_bad.hide()

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
        self.closeImage()
        try:self.win.destroy()
        except: pass
        Gtk.main_quit()

    def next(self, widget):
        if not self.sliderChanged and self.index>=self.endqueue:
            self.msgBox("This is the last file. No more files in this direction.", Gtk.MessageType.ERROR)
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
            self.msgBox("This is the first file. No more files in this direction.", Gtk.MessageType.ERROR)
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
        self.srcfile = os.path.join(self.srcdir, self.srcfiles[self.index])
        print 'Opening {}'.format(self.srcfile)
        self.img  = mpimg.imread(self.srcfile)
        plt.imshow(self.img)
        plt.show()
        self.setupSingleImage()
        
    def closeImage(self):
        self.img = None
        ## TODO: Close image

    def saveImage(self):
        if self.img is None:
            return
        self.saveParasite()
        # TODO: Actually update the DB with info

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
        else: # Label doesn't exist
            self.showButtonAddLabel()

    def addLabel(self, widget):
        '''Add the label as parasite and create a layer for it. If the label already
        exists, only layer needs to be created'''
        self.labels[self.lbl] = True

        self.showButtonDelLabel()
        self.saveImage()


    def markGood(self, widget):
        self.good = True
        self.updateLayout()
        self.saveImage()

    def markBad(self, widget):
        self.good = False
        self.updateLayout()
        self.saveImage()

    def delLabel(self, widget):
        # delete BB, NP and the label if they exist.
        self.labels[self.lbl] = False
        self.layers[self.lbl] = False
        
        self.showButtonAddLabel()
        self.saveImage()

    def msgBox(self, message, typ=Gtk.MessageType.INFO):
        mBox = Gtk.MessageDialog(parent=None, flags=0, message_type=typ, buttons=Gtk.ButtonsType.OK, text=message)
        mBox.run()
        mBox.destroy()

    def saveParasite(self):
        if self.img is None:
            return
        ## TODO: Save parasite info in a DB file

    def createLayer(self, lname, lmode, newlayer=False):
        return None


    # Iconview for label/class selection
    def initIconView(self, wtree):
        self.store = self.create_store()
        self.fill_store()
        sw = wtree.get_object("labels_window")

        iconView = Gtk.IconView(self.store)
        iconView.set_selection_mode(Gtk.SelectionMode.SINGLE)
        iconView.set_text_column(0)
        iconView.set_pixbuf_column(1)

        iconView.connect("selection-changed", self.iconSelectionChanged)
        sw.add(iconView)
        iconView.grab_focus()
        self.icon_view = iconView

    def create_store(self):
        store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str)
        store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        return store
    
    def fill_store(self):
        self.store.clear()
        for lbl in self.classes:
            icon = Gtk.Image()
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

ImageSorter("/home/maheriya/Projects/IMAGES/DATASETS/imagesets/ImageNet/ILSVRC_manual_download/stair/n04314914-stair-step")


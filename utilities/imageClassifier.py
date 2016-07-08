#!/usr/bin/env python
#
# This script allows user to classify an image for use with 'classifiction' or 'detection'
# tasks. Once images are marked as such, clicking 'Copy Files' button creates two
# directories, one each for 'cls' and 'det' tasks. A single image can be classified for
# use with both classification and detection tasks, and will be copied (linked) in both
# '<srcdir>.cls' and '<srcdir>.det' directories.
import os, sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import pickle
import shutil

scriptpath = os.path.dirname(os.path.realpath( __file__ ))
color_red    = Gdk.Color(0xdddd, 0x2222, 0x3333)
color_green  = Gdk.Color(0x2222, 0xdddd, 0x3333)
color_yellow = Gdk.Color(0xdddd, 0xdddd, 0x3333)
class ImageClassifier:
    def __init__(self, imgdir):
        self.done       = False
        self.srcdir     = os.path.realpath(imgdir)
        self.tgtdirCls  = imgdir+'.cls'
        self.tgtdirDet  = imgdir+'.det'
        self.flags      = {'cls': {}, 'det': {}}
        self.cls        = self.flags['cls']
        self.det        = self.flags['det']
        self.procClsSwitchChange = False
        self.procDetSwitchChange = False
        self.img_width  = 0
        self.img_height = 0
        self.setupGUI()

        ## Look for DB file and use it to bootstrap if it exists
        self.dbfilename = os.path.join(self.srcdir, '.cls.db')
        if os.path.exists(self.dbfilename):
            with open(self.dbfilename, 'r') as f:
                self.flags = pickle.load(f)
                self.cls = self.flags['cls']
                self.det = self.flags['det']
            f.close()
        self.setupFiles()
        self.openImage()
        self.updateLayout()
        Gtk.main()

    def setupGUI(self):
        self.gladefile = os.path.join(scriptpath, "imageClassifier.glade")
        self.wtree = Gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        funcmap = {
                "on_prev_button_clicked"       : self.prev,
                "on_next_button_clicked"       : self.next,
                "on_quit_button_clicked"       : self.quit,
                "on_addLabelsWindow_destroy"   : self.quit,
                "on_cls_switch_state_set"      : self.clsStateChanged,
                "on_det_switch_state_set"      : self.detStateChanged,
                "on_btn_mvfiles_clicked"       : self.copyImages,
                "on_slider_value_changed"      : self.indexChanged,
                "on_btn_sortcls_clicked"       : self.sortOnCls,
                "on_btn_sortdet_clicked"       : self.sortOnDet,
                "on_btn_sortfilenames_clicked" : self.sortOnFilename,
        }
        self.wtree.connect_signals(funcmap)

        # # Get all the handles
        self.win          = self.wtree.get_object("addLabelsWindow")
        self.image        = self.wtree.get_object("main_image")
        # new
        self.btn_prev     = self.wtree.get_object("prev_button")
        self.btn_next     = self.wtree.get_object("next_button")
        self.slider       = self.wtree.get_object("slider")
        self.slider_adj   = self.wtree.get_object("slider_adj")
        #
        self.lbl_imgname  = self.wtree.get_object("imgname_label")
        self.lbl_move     = self.wtree.get_object("move_label")
        self.lbl_cls      = self.wtree.get_object("cls_label")
        self.lbl_det      = self.wtree.get_object("det_label")
        self.cls_evbx     = self.wtree.get_object("cls_evbx")     # To change bg color of cls label
        self.det_evbx     = self.wtree.get_object("det_evbx")     # To change bg color of det label
        self.clsinfo_evbx = self.wtree.get_object("clsinfo_evbx") # To change bg color of clsinfo label
        self.detinfo_evbx = self.wtree.get_object("detinfo_evbx") # To change bg color of detinfo label
        self.cls_switch   = self.wtree.get_object("cls_switch")
        self.det_switch   = self.wtree.get_object("det_switch")
        self.win.show_all()

    def setupFiles(self):
        self.srcfiles = []
        for fname in os.listdir(self.srcdir):
            ext = os.path.splitext(fname)[1].lower()
            # Find all of the supported files in the srcdir
            if ext != '.jpg' and ext != '.jpeg' and ext != '.png' and ext != '.bmp':
                continue
            self.srcfiles.append(fname)
            if not fname in self.cls or not fname in self.det:
                (img_width, img_height) = self.getImageSize(fname) # Get size of the image
            if not fname in self.cls:
                # If the flag doesn't exist for this file, add it based on size
                if img_width >= 200 and img_height >= 200:
                    self.cls[fname] = True
                else:
                    self.cls[fname] = False
            if not fname in self.det:
                # If the flag doesn't exist for this file, add it based on size
                if img_width >= 300 and img_height >= 300:
                    self.det[fname] = True
                else:
                    self.det[fname] = False
        if len(self.srcfiles) == 0:
            self.msgBox("Source directory {} didn't contain any images.".format(self.srcdir), Gtk.MessageType.ERROR)
            return
        print("There are total {} images".format(len(self.srcfiles)))
        self.clsimages = [img for img in self.cls if self.cls[img]]
        self.detimages = [img for img in self.det if self.det[img]]
        self.numfiles = len(self.srcfiles)
        self.srcfiles.sort()
        self.srcfiles_sorted = list(self.srcfiles)
        self.endqueue = len(self.srcfiles) - 1
        self.index = 0
        self.sliderChanged = False # To indicate change of index by user via slider
        self.updateSlider  = False # To indicate that slider should be updated due to next/prev button presses
        self.saveDB()

    def updateLayout(self):
        ## Update labels text
        self.lbl_imgname.set_text(self.srcfile)
        self.clsimages = [img for img in self.cls if self.cls[img]]
        self.detimages = [img for img in self.det if self.det[img]]
        cntcls = len(self.clsimages)
        cntdet = len(self.detimages)
        self.lbl_move.set_text('Classification: {cntc:d} image{cs}; Detection: {cntd} image{ds}'.format(cntc=cntcls, cntd=cntdet,
                                                                                                        cs='' if cntcls==1 else 's',
                                                                                                        ds='' if cntdet==1 else 's'))
        # Update cls label bg 
        if self.cls[self.srcfile]:
            self.cls_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        else:
            self.cls_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        # Update det label bg
        if self.det[self.srcfile]:
            self.det_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        else:
            self.det_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        ## Size suitability for classification (update info label bg)
        if (self.img_width < 200 or self.img_height < 200):
            self.clsinfo_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        elif ((self.img_width < 300 and self.img_width >= 200) or
            (self.img_height < 300 and self.img_height >= 200)):
            self.clsinfo_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_yellow)
        else:
            self.clsinfo_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)

        ## Size suitability for detection  (update info label bg)
        if (self.img_width < 300 or self.img_height < 300):
            self.detinfo_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        else:
            self.detinfo_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        ##


        # Update slider max
        self.slider_adj.set_upper(self.numfiles)

    def quit(self, widget=None):
        if not self.done:
            self.done = True
            self.closeImage()
            try: self.win.destroy()
            except: pass
            print("Saving image flags...")
            self.saveDB()
            Gtk.main_quit()

    def next(self, widget=None):
        if not self.sliderChanged and self.index>=self.endqueue:
            #self.msgBox("This is the last file. No more files in this direction.", Gtk.MessageType.ERROR)
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

    def prev(self, widget=None):
        if not self.sliderChanged and self.index<=0:
            #self.msgBox("This is the first file. No more files in this direction.", Gtk.MessageType.ERROR)
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

    def clsStateChanged(self, widget=None, state=True):
        self.cls[self.srcfile] = state
        self.updateLayout()
        #if not self.procClsSwitchChange:
        #    self.saveDB()
        self.procClsSwitchChange = False

    def detStateChanged(self, widget=None, state=True):
        self.det[self.srcfile] = state
        self.updateLayout()
        #if not self.procDetSwitchChange:
        #    self.saveDB()
        self.procDetSwitchChange = False

    def updateSwitches(self):
        ## Set cls_switch and det_switch state based on current cls/det flags for the just opened file
        self.procClsSwitchChange = True
        self.cls_switch.set_state(self.cls[self.srcfile])
        self.procDetSwitchChange = True
        self.det_switch.set_state(self.det[self.srcfile])

    def copyImages(self, widget=None):
        self.saveDB()
        # Clean up existing directories if any.
        if os.path.exists(self.tgtdirCls):
            shutil.rmtree(self.tgtdirCls)
        os.mkdir(self.tgtdirCls)
        if os.path.exists(self.tgtdirDet):
            shutil.rmtree(self.tgtdirDet)
        os.mkdir(self.tgtdirDet)

        self.clsimages = [img for img in self.cls if self.cls[img]]
        self.detimages = [img for img in self.det if self.det[img]]
        srcdir = os.path.basename(self.srcdir)
        for fname in self.clsimages:
            try:
                os.system("ln -s '../{s}/{f}' '{t}'".format(s=srcdir, t=self.tgtdirCls, f=fname))
            except:
                print("Couldn't link {f} in {t}".format(f=fname, t=self.tgtdirCls))
        for fname in self.detimages:
            try:
                os.system("ln -s '../{s}/{f}' '{t}'".format(s=srcdir, t=self.tgtdirDet, f=fname))
            except:
                print("Couldn't link {f} in {t}".format(f=fname, t=self.tgtdirCls))
        self.msgBox('Copied\n\t{cntc} classification images and \n\t{cntd} detection images to\n{c} and {d} directories'.format(c=os.path.basename(self.tgtdirCls),
                                                                                                d=os.path.basename(self.tgtdirDet),
                                                                                                cntc=len(self.clsimages),
                                                                                                cntd=len(self.detimages)))
    def getImageSize(self, srcfile):
        (img_width, img_height) = (0,0)
        pixbuf = None
        img = Gtk.Image()
        try:
            img.set_from_file(os.path.join(self.srcdir, srcfile))
            pixbuf = img.get_pixbuf()
        except:
            print 'Error while opening {}'.format(srcfile)
            return (img_width, img_height)

        if pixbuf is not None:
            img_width, img_height = pixbuf.get_width(), pixbuf.get_height()
        return (img_width, img_height)

    def openImage(self):
        self.srcfile = self.srcfiles[self.index]
        pixbuf = None
        try:
            self.image.set_from_file(os.path.join(self.srcdir, self.srcfile))
            pixbuf = self.image.get_pixbuf()
        except:
            print 'Error while opening {} at index {}'.format(self.srcfile, self.index)
            return

        if pixbuf is not None:
            self.img_width, self.img_height = pixbuf.get_width(), pixbuf.get_height()
        else:
            self.img_width, self.img_height = 0, 0
        self.resizeImage()
        self.updateSwitches()

    def closeImage(self):
        pass

    def indexChanged(self, widget=None):
        self.slider.set_restrict_to_fill_level(False)
        self.slider.set_fill_level(self.slider.get_value())
        self.slider.set_show_fill_level(True)
        if self.updateSlider:
            self.updateSlider = False
            return
        self.index = int(self.slider.get_value()) - 1
        self.sliderChanged = True
        #print 'Slider Changed to {}'.format(self.index+1)

    def msgBox(self, message, typ=Gtk.MessageType.INFO):
        mBox = Gtk.MessageDialog(parent=self.win, flags=0, message_type=typ, buttons=Gtk.ButtonsType.OK, text=message)
        mBox.run()
        mBox.destroy()

    def saveDB(self):
        try: dbfile = open(self.dbfilename, 'w')
        except:
            print('Could not open DB file {}'.format(self.dbfilename))
            sys.exit(1)
        pickle.dump(self.flags, dbfile)
        dbfile.close()

    def resizeImage(self):
        pixbuf = self.image.get_pixbuf()
        if pixbuf is not None:
            cur_width, cur_height = pixbuf.get_width(), pixbuf.get_height()
        else:
            cur_width, cur_height = 0, 0

        # Get the size of the widget area
        allocation = self.image.get_allocation()
        dst_width, dst_height = allocation.width-5, allocation.height-5

        if (cur_width > dst_width or cur_height > dst_height):
            # Scale preserving aspect
            sc = min(float(dst_width)/cur_width, float(dst_height)/cur_height)
            new_width = int(sc*cur_width)
            new_height = int(sc*cur_height)
            pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
            self.image.set_from_pixbuf(pixbuf)

    def sortOnCls(self, widget=None):
        self.sorted = 'CLS'
        self.clsimages.sort()
        nonclsimages = [img for img in self.cls if not self.cls[img]]
        nonclsimages.sort()
        self.srcfiles = self.clsimages + nonclsimages
        self.index = 0
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider
        self.openImage()
        self.updateLayout()

    def sortOnDet(self, widget=None):
        self.sorted = 'DET'
        self.detimages.sort()
        nondetimages = [img for img in self.det if not self.det[img]]
        nondetimages.sort()
        self.srcfiles = self.detimages + nondetimages
        self.index = 0
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider
        self.openImage()
        self.updateLayout()

    def sortOnFilename(self, widget=None):
        self.sorted = 'FILENAME'
        self.srcfiles = self.srcfiles_sorted
        self.index = 0
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider
        self.openImage()
        self.updateLayout()
        

#endclass

if len(sys.argv) < 2:
    print("Usage  imageClassifier.py <imgdir>")
    sys.exit(1)
imgdir = os.path.realpath(sys.argv[1])
print('Working on directory {}'.format(imgdir))
ImageClassifier(imgdir)


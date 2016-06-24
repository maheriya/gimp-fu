#!/usr/bin/env python
#
import os, sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import pickle

scriptpath = os.path.dirname(os.path.realpath( __file__ ))
color_red    = Gdk.Color(0xdddd, 0x2222, 0x3333)
color_green  = Gdk.Color(0x2222, 0xdddd, 0x3333)
color_yellow = Gdk.Color(0xdddd, 0xdddd, 0x3333)
class ImageSorter:
    def __init__(self, imgdir):
        self.done       = False
        self.srcdir     = imgdir
        self.tgtdir     = imgdir+'.bad'
        self.flags      = {}
        self.img_width  = 0
        self.img_height = 0
        self.setupGUI()

        ## Look for DB file and use it to bootstrap if it exists
        self.dbfilename = os.path.join(self.srcdir, '.sorter.db')
        if os.path.exists(self.dbfilename):
            with open(self.dbfilename, 'r') as f:
                self.flags = pickle.load(f)
            f.close()
        self.setupFiles()
        self.openImage()
        self.updateLayout()
        Gtk.main()

    def setupGUI(self):
        self.gladefile = os.path.join(scriptpath, "imageSorter.glade")
        self.wtree = Gtk.Builder()
        self.wtree.add_from_file(self.gladefile)
        funcmap = {
                "on_prev_button_clicked"     : self.prev,
                "on_next_button_clicked"     : self.next,
                "on_quit_button_clicked"     : self.quit,
                "on_addLabelsWindow_destroy" : self.quit,
                "on_mark_good_clicked"       : self.markGood,
                "on_mark_bad_clicked"        : self.markBad,
                "on_btn_mvfiles_clicked"     : self.moveBadImages,
                "on_slider_value_changed"    : self.indexChanged,
        }
        self.wtree.connect_signals(funcmap)

        # # Get all the handles
        self.win          = self.wtree.get_object("addLabelsWindow")
        self.image        = self.wtree.get_object("main_image")
        self.btn_mkgood   = self.wtree.get_object("mark_good")
        self.btn_mkbad    = self.wtree.get_object("mark_bad")
        # new
        self.btn_prev     = self.wtree.get_object("prev_button")
        self.btn_next     = self.wtree.get_object("next_button")
        self.slider       = self.wtree.get_object("slider")
        self.slider_adj   = self.wtree.get_object("slider_adj")
        #
        self.lbl_imgname  = self.wtree.get_object("imgname_label")
        self.lbl_move     = self.wtree.get_object("move_label")
        self.lbl_mark     = self.wtree.get_object("mark_label")
        self.lbl_info     = self.wtree.get_object("info_label")
        self.mark_evbx    = self.wtree.get_object("mark_evbx") # To change bg color of mark label
        self.info_evbx    = self.wtree.get_object("info_evbx") # To change bg color of info label
        self.win.show_all()

    def setupFiles(self):
        self.srcfiles = []
        for fname in os.listdir(self.srcdir):
            ext = os.path.splitext(fname)[1].lower()
            # Find all of the supported files in the srcdir
            if ext != '.jpg' and ext != '.jpeg' and ext != '.png' and ext != '.bmp':
                continue
            self.srcfiles.append(fname)
            if not fname in self.flags:
                # If the flag doesn't exist for this file, add it; assume good
                self.flags[fname] = True # True: good, False: bad
        if len(self.srcfiles) == 0:
            self.msgBox("Source directory {} didn't contain any images.".format(self.srcdir), Gtk.MessageType.ERROR)
            return
        self.badimages = [img for img in self.flags if not self.flags[img]]
        self.numfiles = len(self.srcfiles)
        self.srcfiles.sort()
        self.endqueue = len(self.srcfiles) - 1
        self.index = 0
        self.sliderChanged = False # To indicate change of index by user via slider
        self.updateSlider  = False # To indicate that slider should be updated due to next/prev button presses
        self.saveDB()

    def updateLayout(self):
        ## Update labels text
        self.lbl_imgname.set_text(self.srcfile)
        self.badimages = [img for img in self.flags if not self.flags[img]]
        cnt = len(self.badimages)
        self.lbl_move.set_text('{cnt:d} image{s} currently marked as bad.'.format(cnt=cnt, s='' if cnt==1 else 's'))
        self.lbl_mark.set_text('Currently {ar}'.format(ar='accepted' if self.flags[self.srcfile] else 'rejected'))
        self.lbl_info.set_text('({w}x{h})'.format(w=self.img_width, h=self.img_height))

        # Update mark label bg 
        if self.flags[self.srcfile]:
            self.mark_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        else:
            self.mark_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        # Update info label bg
        if (self.img_width < 250 or self.img_height < 250):
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        elif ((self.img_width < 300 and self.img_width >= 250) or
            (self.img_height < 300 and self.img_height >= 250)):
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_yellow)
        else:
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        # Update slider max
        self.slider_adj.set_upper(self.numfiles)
        ## Update buttons
        self.showButtonsGoodBad()

    def showButtonsGoodBad(self):
        if self.flags[self.srcfile]:
            self.btn_mkbad.show()
            self.btn_mkbad.map()
            self.btn_mkgood.hide()
        else:
            self.btn_mkgood.show()
            self.btn_mkgood.map()
            self.btn_mkbad.hide()

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

    def markGood(self, widget=None):
        self.flags[self.srcfile] = True
        self.updateLayout()
        self.saveDB()

    def markBad(self, widget=None):
        self.flags[self.srcfile] = False
        self.updateLayout()
        self.saveDB()

    def moveBadImages(self, widget=None):
        if not os.path.exists(self.tgtdir):
            os.mkdir(self.tgtdir)
        for fname in self.srcfiles:
            good = self.flags[fname]
            simg = os.path.join(self.srcdir, fname)
            timg = os.path.join(self.tgtdir, fname)
            if not good and os.path.exists(simg):
                try:
                    os.system('mv -f {s} {t}'.format(s=simg, t=timg))
                except:
                    print("Couldn't move {} to {}".format(s=fname, t=self.tgtdir))
                finally:
                    # Remove the flag from DB
                    del(self.flags[fname])
        self.setupFiles()
        self.openImage()
        self.updateLayout()

    def openImage(self):
        self.srcfile = self.srcfiles[self.index]
        #print 'Opening {}'.format(self.srcfile)
        self.image.set_from_file(os.path.join(self.srcdir, self.srcfile))

        # get original dimensions
        pixbuf = self.image.get_pixbuf()
        self.img_width, self.img_height = pixbuf.get_width(), pixbuf.get_height()
        self.resizeImage()

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
        mBox = Gtk.MessageDialog(parent=None, flags=0, message_type=typ, buttons=Gtk.ButtonsType.OK, text=message)
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
        cur_width, cur_height = pixbuf.get_width(), pixbuf.get_height()

        # Get the size of the widget area
        allocation = self.image.get_allocation()
        dst_width, dst_height = allocation.width, allocation.height

        if (cur_width > dst_width and cur_height > dst_height):
            # Scale preserving aspect
            sc = min(float(dst_width)/cur_width, float(dst_height)/cur_height)
            new_width = int(sc*cur_width)
            new_height = int(sc*cur_height)
            pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
            self.image.set_from_pixbuf(pixbuf)

#endclass

if len(sys.argv) < 2:
    print("Usage  imageSorter.py <imgdir>")
    sys.exit(1)
imgdir = os.path.realpath(sys.argv[1])
print('Working on directory {}'.format(imgdir))
ImageSorter(imgdir)


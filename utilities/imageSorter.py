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


INITIAL_STATE_GOOD = True # Whether to assume initial state of the image as good (True) or bad (False)

color_red    = Gdk.Color(0xe100, 0x2400, 0x1000)  ## e12410 red
color_orange = Gdk.Color(0xe100, 0x5a00, 0x1000)  ## e15a10 orange
color_yellow = Gdk.Color(0xda00, 0xe600, 0x1600)  ## dae616 yellow
color_green  = Gdk.Color(0x1600, 0xe600, 0x1f00)  ## 16e61f green
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
                "on_sort_goodbad_clicked"    : self.sortOnGoodBad,
                "on_sort_filename_clicked"   : self.sortOnFilename,
                "on_btn_mvfiles_clicked"     : self.moveBadImages,
                "on_slider_value_changed"    : self.indexChanged,
        }
        self.wtree.connect_signals(funcmap)

        # # Get all the handles
        self.win          = self.wtree.get_object("addLabelsWindow")
        self.image        = self.wtree.get_object("main_image")
        self.btn_mkgood   = self.wtree.get_object("mark_good")
        self.btn_mkbad    = self.wtree.get_object("mark_bad")
        self.btn_sortg    = self.wtree.get_object("sort_goodbad")
        self.btn_sortf    = self.wtree.get_object("sort_filename")
        # new
        self.btn_prev     = self.wtree.get_object("prev_button")
        self.btn_next     = self.wtree.get_object("next_button")
        self.slider       = self.wtree.get_object("slider")
        self.slider_adj   = self.wtree.get_object("slider_adj")
        #
        self.lbl_imgname  = self.wtree.get_object("imgname_label")
        self.lbl_move     = self.wtree.get_object("move_label")
        self.lbl_mark     = self.wtree.get_object("mark_label1")
        self.lbl_info     = self.wtree.get_object("info_label")
        self.mark_evbx1   = self.wtree.get_object("mark_evbx1") # To change bg color of mark label1
        self.mark_evbx2   = self.wtree.get_object("mark_evbx2") # To change bg color of mark label2
        self.mark_evbx3   = self.wtree.get_object("mark_evbx3") # To change bg color of mark label3
        self.mark_evbx4   = self.wtree.get_object("mark_evbx4") # To change bg color of mark label4
        self.info_evbx    = self.wtree.get_object("info_evbx") # To change bg color of info label
        self.win.show_all()

    def setupFiles(self):
        self.srcfiles = []
        self.sorted = 'Filename'
        for fname in os.listdir(self.srcdir):
            ext = os.path.splitext(fname)[1].lower()
            # Find all of the supported files in the srcdir
            if ext != '.jpg' and ext != '.jpeg' and ext != '.png' and ext != '.bmp':
                continue
            self.srcfiles.append(fname)
            if not fname in self.flags:
                # If the flag doesn't exist for this file, add it;
                self.flags[fname] = INITIAL_STATE_GOOD # True: good, False: bad
        if len(self.srcfiles) == 0:
            self.msgBox("Source directory {} didn't contain any images.".format(self.srcdir), Gtk.MessageType.ERROR)
            return
        print("There are total {} images".format(len(self.srcfiles)))
        self.badimages = [img for img in self.flags if not self.flags[img]]
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
        self.badimages = [img for img in self.flags if not self.flags[img]]
        self.badimages.sort()
        self.goodimages = [img for img in self.flags if self.flags[img]]
        self.goodimages.sort()
        cnt = len(self.badimages)
        cntgood = len(self.goodimages) #self.numfiles - cnt
        self.lbl_move.set_text('{cnt:d} image{s} currently marked as bad ({cntgood:d} good image{gs}).'.format(
            cnt=cnt, s='' if cnt==1 else 's', cntgood=cntgood, gs='' if cntgood==1 else 's'))
        self.lbl_mark.set_text('{ar}'.format(ar='Accepted' if self.flags[self.srcfile] else 'Rejected'))
        self.lbl_info.set_text('({w}x{h})'.format(w=self.img_width, h=self.img_height))

        # Update mark label bg 
        if self.flags[self.srcfile]:
            self.mark_evbx1.modify_bg(Gtk.StateFlags.NORMAL, color_green)
            self.mark_evbx2.modify_bg(Gtk.StateFlags.NORMAL, color_green)
            #self.mark_evbx4.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        else:
            self.mark_evbx1.modify_bg(Gtk.StateFlags.NORMAL, color_red)
            self.mark_evbx2.modify_bg(Gtk.StateFlags.NORMAL, color_red)
            self.mark_evbx3.modify_bg(Gtk.StateFlags.NORMAL, color_red)
            #self.mark_evbx4.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        # Update info label bg
        if (self.img_width < 200 or self.img_height < 200):
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_red)
            self.mark_evbx3.modify_bg(Gtk.StateFlags.NORMAL, color_red)
        elif ((self.img_width < 260 and self.img_width >= 200) or
            (self.img_height < 260 and self.img_height >= 200)):
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_orange)
            self.mark_evbx3.modify_bg(Gtk.StateFlags.NORMAL, color_orange)
        elif ((self.img_width < 300 and self.img_width >= 260) or
            (self.img_height < 300 and self.img_height >= 260)):
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_yellow)
            self.mark_evbx3.modify_bg(Gtk.StateFlags.NORMAL, color_yellow)
        else:
            self.info_evbx.modify_bg(Gtk.StateFlags.NORMAL, color_green)
            self.mark_evbx3.modify_bg(Gtk.StateFlags.NORMAL, color_green)
        # Update slider max
        self.slider_adj.set_upper(self.numfiles)
        ## Update buttons
        self.showButtonsGoodBad()
        self.showButtonsSort()

    def showButtonsGoodBad(self):
        if self.flags[self.srcfile]:
            self.btn_mkbad.show()
            self.btn_mkbad.map()
            self.btn_mkgood.hide()
        else:
            self.btn_mkgood.show()
            self.btn_mkgood.map()
            self.btn_mkbad.hide()

    def showButtonsSort(self):
        if self.sorted == 'Filename':
            # Sorted on filename order. Show sortg button. Hide sortf button
            self.btn_sortg.show()
            self.btn_sortg.map()
            self.btn_sortf.hide()
        else:
            # Sorted on Good/Bad order. Show sortf button. Hide sortg button
            self.btn_sortf.show()
            self.btn_sortf.map()
            self.btn_sortg.hide()

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
        #self.saveDB()

    def markBad(self, widget=None):
        self.flags[self.srcfile] = False
        self.updateLayout()
        #self.saveDB()

    def moveBadImages(self, widget=None):
        self.saveDB()
        if not os.path.exists(self.tgtdir):
            os.mkdir(self.tgtdir)
        for fname in self.srcfiles:
            good = self.flags[fname]
            simg = os.path.join(self.srcdir, fname)
            timg = os.path.join(self.tgtdir, fname)
            if not good and os.path.exists(simg):
                try:
                    os.system("mv -f '{s}' '{t}'".format(s=simg, t=timg))
                except:
                    print("Couldn't move {} to {}".format(s=fname, t=self.tgtdir))
                finally:
                    # Remove the flag from DB
                    del(self.flags[fname])
        self.setupFiles()
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider

        self.openImage()
        self.updateLayout()

    def openImage(self):
        self.srcfile = self.srcfiles[self.index]
        #print 'Opening {} at index {}'.format(self.srcfile, self.index)
        pixbuf = None
        try:
            self.image.set_from_file(os.path.join(self.srcdir, self.srcfile))
            # get original dimensions
            pixbuf = self.image.get_pixbuf()
        except:
            print 'Error while opening {} at index {}'.format(self.srcfile, self.index)
            return


        if pixbuf is not None:
            self.img_width, self.img_height = pixbuf.get_width(), pixbuf.get_height()
        else:
            self.img_width, self.img_height = 0, 0
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

    def sortOnFilename(self, widget=None):
        self.sorted = 'Filename'
        self.srcfiles = self.srcfiles_sorted
        self.index = 0
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider

        self.openImage()
        self.updateLayout()
        
    def sortOnGoodBad(self, widget=None):
        self.sorted = 'GoodBad'
        self.srcfiles = self.goodimages+self.badimages
        self.index = 0
        self.updateSlider = True
        self.slider.set_value(self.index+1) # Update slider

        self.openImage()
        self.updateLayout()

#endclass

if len(sys.argv) < 2:
    print("Usage  imageSorter.py <imgdir>")
    sys.exit(1)
imgdir = os.path.realpath(sys.argv[1])
print('Working on directory {}'.format(imgdir))
ImageSorter(imgdir)


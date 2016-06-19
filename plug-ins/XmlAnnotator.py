import os
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom

'''
Provides two methods:
addObject() : To add an object at a time to the annotation
write()  : to finally  write the XML annotation file.
'''
class XmlAnnotator:
    def __init__(self, tgtdir, imgname, width, height):
        """
        Creates an XML annotation file in tgtdir directory.
        width  : width of all images
        height : height of all images
        The XML format is compatible with VOC XML annotations.
        """
        self.tgtdir  = tgtdir
        self.imgname = imgname
        self.width   = width
        self.height  = height
        self.depth   = 3
        # Create start of XML annotation
        self.top = None
        self.top = Element('annotation')
        self.addFileName()
        self.addSize()

    def write(self):
        (xmlfile, ext) = os.path.splitext(self.imgname)
        with open(os.path.join(self.tgtdir, xmlfile+'.xml'), 'w') as xfile:
            xfile.write(self.prettify(self.top))
            xfile.close()

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def addFileName(self):
        filename = SubElement(self.top, 'filename')
        filename.text = self.imgname
        
    def addSize(self):
        el_size        = SubElement(self.top, 'size')
        el_size_w      = SubElement(el_size, 'width')
        el_size_w.text = str(self.width)
        el_size_h      = SubElement(el_size, 'height')
        el_size_h.text = str(self.height)
        el_size_d      = SubElement(el_size, 'depth')
        el_size_d.text = str(self.depth)
    
    def addObject(self, name, obj):
        '''
        obj is the DVIA object of the form:
        {'np': (), 'bb': (), 'npLayer': None, 'bbLayer': None, 'index': None}
        '''
        object = SubElement(self.top, 'object')
        # Class or category label
        object_name             = SubElement(object, 'name')
        object_name.text        = name
        # Bounding Box
        object_bndbox           = SubElement(object, 'bndbox')
        object_bndbox_xmin      = SubElement(object_bndbox, 'xmin')
        ## Special hack for VOC: if xmin is 0, make it 1
        object_bndbox_xmin.text = str(obj['bb'][0] if obj['bb'][0]!=0 else 1)
        object_bndbox_ymin      = SubElement(object_bndbox, 'ymin')
        object_bndbox_ymin.text = str(obj['bb'][1] if obj['bb'][1]!=0 else 1)
        object_bndbox_xmax      = SubElement(object_bndbox, 'xmax')
        object_bndbox_xmax.text = str(obj['bb'][2] if obj['bb'][2]!=0 else 1)
        object_bndbox_ymax      = SubElement(object_bndbox, 'ymax')
        object_bndbox_ymax.text = str(obj['bb'][3] if obj['bb'][3]!=0 else 1)
        # Nearest Point
        object_np        = SubElement(object, 'np')
        object_np_x      = SubElement(object_np, 'x')
        if (obj['np'][0]==0):
            obj['np'][0]=1
        object_np_x.text = str(obj['np'][0])
        object_np_y      = SubElement(object_np, 'y')
        if (obj['np'][1]==0):
            obj['np'][1]=1
        object_np_y.text = str(obj['np'][1])
        #
        object_pose      = SubElement(object, 'pose')
        object_pose.text = 'front'


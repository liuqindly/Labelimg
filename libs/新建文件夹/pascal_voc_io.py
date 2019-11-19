#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs

XML_EXT = '.xml'
ENCODE_METHOD = 'utf-8'

class PascalVocWriter:

    def __init__(self, foldername, filename, imgSize,databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = None

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        '''reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)'''

    def genXML(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.foldername is None or \
                self.imgSize is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', self.verified)

        folder = SubElement(top, 'folder')
        folder.text = self.foldername

        filename = SubElement(top, 'filename')
        filename.text = self.filename

        if self.localImgPath is not None:
            localImgPath = SubElement(top, 'path')
            localImgPath.text = self.localImgPath

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.databaseSrc

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        
        width.text = str(self.imgSize[1])
        height.text = str(self.imgSize[0])
        if len(self.imgSize) == 3:
            depth.text = str(self.imgSize[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def addBndBox(self, xmin, ymin, xmax, ymax, name, pose, unique, difficult,polygonLabel,polygontype,polygonpoint):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['pose'] = pose
        bndbox['unique'] = unique
        bndbox['difficult'] = difficult
        bndbox['polygonlabel'] = polygonLabel
        bndbox['polygontype'] = polygontype
        bndbox['polygonpoint'] = polygonpoint
        self.boxlist.append(bndbox)

    def appendObjects(self, top):
        for each_object in self.boxlist:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            try:
                name.text = str(each_object['name'])
            except NameError:
                # Py3: NameError: name 'str' is not defined
                name.text = each_object['name']
            pose = SubElement(object_item, 'pose')
            unique = SubElement(object_item, 'unique')
            pose.text =  str(each_object['pose'])
            unique.text = str(each_object['unique'])
            truncated = SubElement(object_item, 'truncated')
            if int(each_object['ymax']) == int(self.imgSize[0]) or (int(each_object['ymin'])== 1):
                truncated.text = "1" # max == height or min
            elif (int(each_object['xmax'])==int(self.imgSize[1])) or (int(each_object['xmin'])== 1):
                truncated.text = "1" # max == width or min
            else:
                truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str( bool(each_object['difficult']) & 1 )
            bndbox = SubElement(object_item, 'bndbox')
            xmin = SubElement(bndbox, 'xmin')
            xmin.text = str(each_object['xmin'])
            ymin = SubElement(bndbox, 'ymin')
            ymin.text = str(each_object['ymin'])
            xmax = SubElement(bndbox, 'xmax')
            xmax.text = str(each_object['xmax'])
            ymax = SubElement(bndbox, 'ymax')
            ymax.text = str(each_object['ymax'])
            if each_object['polygontype'] != None:
                polygonpointxbox = []
                polygonpointybox = []
                polygon = SubElement(object_item, 'polygon')
                if each_object['polygonlabel'] != None:
                    polygonlabel = SubElement(polygon,'polygonlabel')
                    polygonlabel.text = str(each_object['polygonlabel'])
                polygontype = SubElement(polygon, 'polygontype')
                polygontype.text = str(each_object['polygontype'])
                polygonpoint = SubElement(polygon, 'polygonpoint')
                for item in each_object['polygonpoint']:
                    polygonpointxbox.append(int(item[0]))
                    polygonpointybox.append(int(item[1]))
                
                polygonpointx = SubElement(polygonpoint, 'x')
                polygonpointy = SubElement(polygonpoint, 'y')
                polygonpointx.text = str(polygonpointxbox)
                polygonpointy.text = str(polygonpointybox)


    def save(self, targetFile=None):
        root = self.genXML()
        self.appendObjects(root)
        out_file = None
        if targetFile is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)

        prettifyResult = self.prettify(root)
        out_file.write(prettifyResult.decode('utf8'))
        out_file.close()


class PascalVocReader:

    def __init__(self, filepath):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.filepath = filepath
        self.verified = False
        try:
            self.parseXML()
        except:
            pass

    def getShapes(self):
        return self.shapes

    def addShape(self, label, pose, unique, bndbox, difficult,polygonlabel = None,polygontype= None,polygonpointx=[],polygonpointy=[]):
        xmin = int(bndbox.find('xmin').text)
        ymin = int(bndbox.find('ymin').text)
        xmax = int(bndbox.find('xmax').text)
        ymax = int(bndbox.find('ymax').text)
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, pose, unique, points, None, None, difficult,polygonlabel,polygontype,polygonpointx,polygonpointy))

    def parseXML(self):
        assert self.filepath.endswith(XML_EXT), "Unsupport file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()
        filename = xmltree.find('filename').text
        try:
            verified = xmltree.attrib['verified']
            if verified == 'yes':
                self.verified = 'yes'
            elif verified == 'yes1':
                self.verified = 'yes1'
            elif verified == 'yes2':
                self.verified = 'yes2'
        except KeyError:
            self.verified = None

        for object_iter in xmltree.findall('object'):
            bndbox = object_iter.find("bndbox")
            label = object_iter.find('name').text
            pose = object_iter.find('pose').text
            if object_iter.find('unique') is not None:
                unique = object_iter.find('unique').text
            else:
                unique = '0'
            # Add chris
            difficult = False
            if object_iter.find('difficult') is not None:
                difficult = bool(int(object_iter.find('difficult').text))
            try:
                try:
                    polygon = object_iter.find('polygon')
                    polygonlabel = polygon.find('polygonlabel').text
                    polygontype = polygon.find('polygontype').text
                    polygonpoint = polygon.find('polygonpoint')
                    polygonpointx = polygonpoint.find('x').text
                    polygonpointy = polygonpoint.find('y').text
                    self.addShape(label, pose, unique, bndbox, difficult,polygonlabel = polygonlabel,polygontype=polygontype,polygonpointx=polygonpointx,polygonpointy=polygonpointy)
                except:
                    polygon = object_iter.find('polygon')
                    polygontype = polygon.find('polygontype').text
                    polygonpoint = polygon.find('polygonpoint')
                    polygonpointx = polygonpoint.find('x').text
                    polygonpointy = polygonpoint.find('y').text
                    self.addShape(label, pose, unique, bndbox, difficult,polygontype=polygontype,polygonpointx=polygonpointx,polygonpointy=polygonpointy)
            except:
                self.addShape(label, pose, unique, bndbox, difficult,)
        return True


    
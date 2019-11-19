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
            top.set('verified', 'yes')

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

    def addBndBox(self,name, pose, unique, difficult,polygontype,x,y,inpolygon=[]):
        bndbox = {'x': x, 'y': y}
        bndbox['name'] = name
        bndbox['pose'] = pose
        bndbox['unique'] = unique
        bndbox['difficult'] = difficult
        bndbox['polygontype'] = polygontype
        bndbox['inpolygon'] = inpolygon
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
            truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str( bool(each_object['difficult']) & 1 )
            polygontype = SubElement(object_item, 'polygontype')
            polygontype.text = str(each_object['polygontype'])
            points = SubElement(object_item,'points')
            x = SubElement(points, 'x')
            x.text = str(each_object['x'])
            y = SubElement(points, 'y')
            y.text = str(each_object['y'])
            if each_object['inpolygon'] != []:
                for item in each_object['inpolygon']:
                    inpolygon = SubElement(object_item, 'polygon')
                    points = SubElement(inpolygon,'points')
                    x = SubElement(points, 'x')
                    x.text = str(item['x'])
                    y = SubElement(points, 'y')
                    y.text = str(item['y'])
                    polygontype = SubElement(inpolygon, 'polygontype')
                    polygontype.text = str(item['polygontype'])


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
            print('wrong loading xml'+filepath)

    def getShapes(self):
        return self.shapes

    def addShape(self, label, pose, unique, x,y, difficult,shape_type,innerpolygon):
        self.shapes.append((label, pose, unique, x,y, None, None, difficult,shape_type,innerpolygon))

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
            innerpolygon = []
            points = object_iter.find("points")
            x = list(eval(points.find('x').text))
            y = list(eval(points.find('y').text))
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
            shape_type = object_iter.find('polygontype').text
            try:
                for polygon in object_iter.findall('polygon'):
                    points1 = polygon.find('points')
                    x1 = list(eval(points1.find('x').text))
                    y1 = list(eval(points1.find('y').text))
                    shape_type1 = polygon.find('polygontype').text
                    innerpolygon.append(dict(
                        x = x1,
                        y = y1,
                        shape_type = shape_type1
                    ))
            except:
                pass
            self.addShape(label,pose,unique,x,y,difficult,shape_type,innerpolygon)
        return True


    
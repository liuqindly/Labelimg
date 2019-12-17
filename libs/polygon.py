import copy
import math

from qtpy import QtCore
from qtpy import QtGui
import sys
import utils


# TODO(unknown):
# - [opt] Store paths instead of creating new ones at each paint.


DEFAULT_LINE_COLOR = QtGui.QColor(255, 0, 0, 255)
DEFAULT_FILL_COLOR = QtGui.QColor(255, 0, 0, 128)
DEFAULT_SELECT_LINE_COLOR = QtGui.QColor(255, 255, 255)
DEFAULT_SELECT_FILL_COLOR = QtGui.QColor(0, 128, 255, 155)
DEFAULT_VERTEX_FILL_COLOR = QtGui.QColor(0, 255, 0, 255)
DEFAULT_HVERTEX_FILL_COLOR = QtGui.QColor(255, 0, 0)


class Polygon(object):

    P_SQUARE, P_ROUND = 0, 1

    MOVE_VERTEX, NEAR_VERTEX = 0, 1

    # The following class variables influence the drawing of all shape objects.
    line_color = DEFAULT_LINE_COLOR
    fill_color = DEFAULT_FILL_COLOR
    select_line_color = DEFAULT_SELECT_LINE_COLOR
    select_fill_color = DEFAULT_SELECT_FILL_COLOR
    vertex_fill_color = DEFAULT_VERTEX_FILL_COLOR
    hvertex_fill_color = DEFAULT_HVERTEX_FILL_COLOR
    point_type = P_ROUND
    point_size = 2
    scale = 1.0

    def __init__(self, label=None, line_color=None, fill_color=None,shape_type=None):
        self.label = label  
        self.points = []
        self.fill = False
        self.selected = False
        self.shape_type = shape_type
        self.pose = "Unspecified"
        self.difficult = 0
        self.unique = 0
        self.innerpolygons = []
        self._highlightIndex = None
        self._highlightMode = self.NEAR_VERTEX
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (2, self.P_SQUARE),
        }

        self._closed = False

        if line_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.line_color = line_color
        else:
            self.line_color = None
        if fill_color is not None:
            # Override the class line_color attribute
            # with an object attribute. Currently this
            # is used for drawing the pending line a different color.
            self.fill_color = fill_color
        else:
            self.fill_color = None
        self.shape_type = shape_type

    @property
    def shape_type(self):
        return self._shape_type

    @shape_type.setter
    def shape_type(self, value):
        if value is None:
            value = 'polygon'
        if value not in ['polygon', 'rectangle', 'point',
           'line', 'circle', 'linestrip','x-rectangle']:
            raise ValueError('Unexpected shape_type: {}'.format(value))
        self._shape_type = value

    def close(self):
        self._closed = True

    def addPoint(self, point):
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)

    def popPoint(self):
        if self.points:
            return self.points.pop()
        return None

    def insertPoint(self, i, point):
        self.points.insert(i, point)

    def isClosed(self):
        return self._closed

    def setOpen(self):
        self._closed = False

    def getRectFromLine(self, pt1, pt2):
        x1, y1 = pt1.x(), pt1.y()
        x2, y2 = pt2.x(), pt2.y()
        return QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)

    def paint(self, painter):
        if self.points:
            color = self.select_line_color \
                if self.selected else self.line_color
            pen = QtGui.QPen(color)
            # Try using integer sizes for smoother drawing(?)
            pen.setWidth(max(1, int(round(1.0 / self.scale))))
            painter.setPen(pen)

            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()
            if self.shape_type == 'rectangle':
                assert len(self.points) in [1, 2, 4]
                if len(self.points) == 2:
                    rectangle = self.getRectFromLine(*self.points)
                    line_path.addRect(rectangle)
                if len(self.points) == 4:
                    rectangle = self.getRectFromLine(self.points[0],self.points[2])
                    line_path.addRect(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i)
            elif self.shape_type == "circle":
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = self.getCircleRectFromLine(self.points)
                    line_path.addEllipse(rectangle)
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i)
                # self.drawVertex(testpoint, 0)
            elif self.shape_type == "linestrip":
                line_path.moveTo(self.points[0])
                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i)
            else:
                line_path.moveTo(self.points[0])
                # Uncommenting the following line will draw 2 paths
                # for the 1st vertex, and make it non-filled, which
                # may be desirable.
                # self.drawVertex(vrtx_path, 0)

                for i, p in enumerate(self.points):
                    line_path.lineTo(p)
                    self.drawVertex(vrtx_path, i)
                if self.isClosed():
                    line_path.lineTo(self.points[0])
            if self.shape_type == 'rectangle':
                min_x = sys.maxsize
                min_y = sys.maxsize
                for point in self.points:
                    min_x = min(min_x, point.x())
                    min_y = min(min_y, point.y())
                if min_x != sys.maxsize and min_y != sys.maxsize:
                    # font = QtCore.QFont("Microsoft YaHei",10, QFont.Bold)
                    #font.setPointSize(10)
                    #font.setBold(True)
                    # painter.setFont(font)
                    if self.label != None:
                        painter.drawText(min_x, min_y, self.label)
            else:
                painter.drawText(self.points[0].x(),self.points[0].y(),self.label)
            painter.drawPath(line_path)
            painter.drawPath(vrtx_path)
            painter.fillPath(vrtx_path, self.vertex_fill_color)
            if self.fill:
                color = self.select_fill_color \
                    if self.selected else self.fill_color
                painter.fillPath(line_path, color)
            if self.innerpolygons:
                for polygon in self.innerpolygons:
                    polygon.paint(painter)
        

    def drawVertex(self, path, i):
        d = self.point_size / self.scale
        shape = self.point_type
        point = self.points[i]
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self.vertex_fill_color = self.hvertex_fill_color
        else:
            self.vertex_fill_color = Polygon.vertex_fill_color
        if shape == self.P_SQUARE:
              path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        min_distance = float('inf')
        min_i = None
        for i, p in enumerate(self.points):
            dist = utils.distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i
    
    def nearest2Vertex(self, point):
        min_distance1 = float('inf')
        min_distance2 = float('inf')
        min1_i = None
        min2_i = None
        for i, p in enumerate(self.points):
            dist = utils.distance(p - point)
            if dist < min_distance1:
                min_distance1 = dist
                min1_i = i
        for i, p in enumerate(self.points):
            dist = utils.distance(p - point)
            if dist < min_distance2 and dist > min_distance1:
                min_distance2 = dist
                min2_i = i
        if min2_i < min1_i:
            return min2_i
        else:
            return min1_i
        

    def nearestEdge(self, point, epsilon):
        min_distance = float('inf')
        post_i = None
        for i in range(len(self.points)):
            line = [self.points[i - 1], self.points[i]]
            dist = utils.distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i
    def nearest1Edge(self, point):
        min_distance = float('inf')
        post_i = None
        for i in range(len(self.points)):
            line = [self.points[i - 1], self.points[i]]
            dist = utils.distancetoline(point, line)
            if dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    def containsPoint(self, point):
        return self.makePath().contains(point)

    def getCircleRectFromLine(self, line):
        """Computes parameters to draw with `QPainterPath::addEllipse`"""
        if len(line) != 2:
            return None
        (c, point) = line
        r = line[0] - line[1]
        d = math.sqrt(math.pow(r.x(), 2) + math.pow(r.y(), 2))
        rectangle = QtCore.QRectF(c.x() - d, c.y() - d, 2 * d, 2 * d)
        return rectangle 

    def getOvalRectFromLine(self,points):
        if len(points) != 3:
            return None
        midpoint = (points[0] + points[1])/2
        r =  midpoint - points[0]
        d =  math.sqrt(math.pow(r.x(), 2) + math.pow(r.y(), 2))
        k = -r.x()/r.y()
        b = (midpoint.x()*points[0].y()-points[0].x()*midpoint.y())/(r.x())
        r2 = points[3] - midpoint
        d2 = math.sqrt(math.pow(r2.x(), 2) + math.pow(r2.y(), 2))


        leftopx = points[0].x() - math.sqrt(d2*d2/(1+(k*k)))
        leftopy = leftopx*k + b
        midtopx = midpoint.x() - math.sqrt(d2*d2/(1+(k*k)))
        midtopy = midtopx*k + b

        rectangle = QtCore.QRectF(leftopx , leftopy, d*2, )




    def makePath(self):
        # if self.shape_type == 'rectangle':
        #     path = QtGui.QPainterPath()
        #     if len(self.points) == 2:
        #         rectangle = self.getRectFromLine(*self.points)
        #         path.addRect(rectangle)
        if self.shape_type == "circle":
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                rectangle = self.getCircleRectFromLine(self.points)
                path.addEllipse(rectangle)
        else:
            path = QtGui.QPainterPath(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
        return path

    def boundingRect(self):
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        self.points = [p + offset for p in self.points]
        if self.innerpolygons != []:
            for polygon in self.innerpolygons:
                polygon.moveBy(offset)

    def moveVertexBy(self, i, offset):
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        self._highlightIndex = None

    def copy(self,type=0):
        shape = Polygon(label=self.label, shape_type=self.shape_type)
        shape.points = [copy.deepcopy(p) for p in self.points]
        shape.fill = self.fill
        shape.selected = self.selected
        copybox = []
        if type == 1:
            for polygon in self.innerpolygons:
                newpolygon = Polygon(label=polygon.label, shape_type=polygon.shape_type)
                
                newpolygon.points = [copy.deepcopy(p) for p in polygon.points]
                newpolygon.fill = self.fill
                newpolygon.line_color = polygon .line_color
                newpolygon.selected = False
                copybox.append(newpolygon)
                
            shape.innerpolygons = copybox
        else:
            pass
        shape._closed = self._closed
        shape.line_color = copy.deepcopy(self.line_color)
        shape.fill_color = copy.deepcopy(self.fill_color)
        return shape

    def __len__(self):
        return len(self.points)

    def __getitem__(self, key):
        return self.points[key]

    def __setitem__(self, key, value):
        self.points[key] = value

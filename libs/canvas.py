
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

#from PyQt4.QtOpenGL import *
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


from libs.shape import Shape
from libs.lib import distance
from libs.polygon import Polygon
import labelme.utils
import math
import numpy as np
CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor

# class Canvas(QGLWidget):


class Canvas(QWidget):
    zoomRequest = pyqtSignal(int)
    scrollRequest = pyqtSignal(int, int)
    newShape = pyqtSignal()
    selectionChanged = pyqtSignal(bool)
    selectionpolChanged = pyqtSignal(bool)
    shapeMoved = pyqtSignal()
    drawingPolygon = pyqtSignal(bool)
    deletePolygon = pyqtSignal()
    CREATE, EDIT, POLYGON , EDITPOLYGON= list(range(4))

    epsilon = 6.0
    polepsilon = 10.0
    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.
        self.mode = self.EDIT
        self.shapes = []
        self.current = None
        self.polygons = []
        self.selectedShape = None  # save the selected shape here
        self.selectedShapeCopy = None
        self.drawingLineColor = QColor(0, 0, 255)
        self.drawingRectColor = QColor(0, 0, 255) 
        self.line = Shape(line_color=self.drawingLineColor)
        self.prevPoint = QPointF()
        self.offsets = QPointF(), QPointF()
        self.scale = 1.0
        self.pixmap = QPixmap()
        self.visible = {}
        self._hideBackround = False
        self.hideBackround = False
        self.hShape = None
        self.hVertex = None
        self._painter = QPainter()
        self._cursor = CURSOR_DEFAULT
        # Menus:
        self.menus = (QMenu(), QMenu())
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)
        self.verified = False
        
        self.moreselected = False
        
        #polygon drawing 
        self.polshapes = []
        self.polcurrent = None
        self.pollineColor = QtGui.QColor(0, 0, 255)
        self.polline = Polygon(line_color=self.pollineColor)
        self.createMode = 'polygon'
        self.polygondrawing = False
        self.shapesBackups = []
        self.selectedpolygon = None
        self.selectedpolygon2 = None
        self.hpolygonVertex = None
        self.hpolygon = None
        self.hpolygonedge = None
        self.tempbox = []


    def setDrawingColor(self, qColor):
        self.drawingLineColor = qColor
        self.drawingRectColor = qColor

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)

    def leaveEvent(self, ev):
        self.restoreCursor()

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def isVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        return self.mode == self.CREATE

    def polygonDrawing(self):
        return self.mode == self.POLYGON

    def polygonEditing(self):
        return self.mode == self.EDITPOLYGON

    def editing(self):
        return self.mode == self.EDIT

    def setEditing(self, valueCreate=False, valuePolygon=False):
        if valueCreate:
            self.mode = self.CREATE
        elif valuePolygon:
            if valuePolygon == 3:
                self.mode = self.EDITPOLYGON
            else:
                self.mode = self.POLYGON   
        else:
            self.mode = self.EDIT
        if valueCreate:  # Create
            self.unHighlight()
            self.deSelectpolygon()
        self.prevPoint = QPointF()
        self.repaint()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
        self.hVertex = self.hShape = None

    def selectedVertex(self):
        return self.hVertex is not None

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        pos = self.transformPos(ev.pos())
        selecting = False
        selecting2 = False
        innerpolygon = None
        if not self.selectedpolygonVertex():
            self.tempbox = []
        self.setToolTip('('+str(int(pos.x()))+'['+str(int(pos.x())+176)+'],'+str(int(pos.y()))+')')
        # Polygon drawing.
        if self.drawing() or self.polygonDrawing():
            self.polline.shape_type = self.createMode
            self.overrideCursor(CURSOR_DRAW)
            if not self.polcurrent:
                return
            color = self.pollineColor
            if self.outOfPixmap(pos):
                # Don't allow the user to draw outside the pixmap.
                # Project the point to the pixmap's edges.
                pos = self.intersectionPoint(self.polcurrent[-1], pos)
            elif len(self.polcurrent) > 1 and self.createMode == 'polygon' and\
                    self.polcloseEnough(pos, self.polcurrent[0]):
                # Attract line to starting point and
                # colorise to alert the user.
                pos = self.polcurrent[0]
                color = self.polcurrent.line_color
                self.overrideCursor(CURSOR_POINT)
                self.polcurrent.highlightVertex(0, Shape.NEAR_VERTEX)
            if self.createMode in ['polygon', 'linestrip']:
                self.polline[0] = self.polcurrent[-1]
                self.polline[1] = pos
            elif self.createMode == 'rectangle':
                self.polline.points = [self.polcurrent[0], pos]
                self.polline.close()
            elif self.createMode == 'circle':
                self.polline.points = [self.polcurrent[0], pos]
                self.polline.shape_type = "circle"
            elif self.createMode == 'line':
                self.polline.points = [self.polcurrent[0], pos]
                self.polline.close()
            elif self.createMode == 'point':
                self.polline.points = [self.polcurrent[0]]
                self.polline.close()
            elif self.createMode == 'x-rectangle':
                if len(self.polcurrent.points)>= 2:
                    if len(self.polcurrent.points) == 2:
                        point1,point2 = self.squarepoint(self.polcurrent.points,pos)
                        self.polcurrent.points = [self.polcurrent.points[0],point1,self.polcurrent.points[1],point2]
                    elif len(self.polcurrent.points) == 4:
                        point1,point2 = self.squarepoint([self.polcurrent.points[0],self.polcurrent.points[2]],pos)
                        self.polcurrent.points[1] = point1
                        self.polcurrent.points[3] = point2
                        self.polcurrent.close()
                    self.polline.points = [self.polcurrent[0],self.polcurrent[2]]
                else:
                    self.polline.points = [self.polcurrent[0], pos]
                
                self.polline.close()
            self.prevPoint = pos
            self.polline.line_color = color
            self.repaint()
            self.polcurrent.highlightClear()
            return


        # Polygon copy moving.
        if Qt.RightButton & ev.buttons() and not self.hpolygonVertex:
            if self.selectedShapeCopy and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMovepolygonShape(self.selectedShapeCopy, pos)
                self.repaint()
            elif self.selectedpolygon:
                self.selectedShapeCopy = self.selectedpolygon.copy()
                self.repaint()
                return
            return 



        # Polygon/Vertex moving.
        if Qt.LeftButton & ev.buttons():
            self.setToolTip('('+str(int(pos.x()))+'['+str(int(pos.x())+176)+'],'+str(int(pos.y()))+')')
            
            if self.selectedpolygonVertex():
                if self.hpolygon.shape_type == 'rectangle':
                    self.boundedMoverectangleVertex(pos)
                elif self.hpolygon.shape_type == 'x-rectangle':
                    if self.tempbox == []:
                        self.tempbox = [self.hpolygon.points[0],self.hpolygon.points[1],self.hpolygon.points[2],self.hpolygon.points[3]]
                    self.boundedMoveXrectangleVertex(pos)
                else:
                    self.boundedMovepolygonVertex(pos)
                self.movingShape = True
                self.shapeMoved.emit()
                self.repaint()
            elif self.selectedpolygon2 and self.prevPoint and self.polygonEditing():
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMovepolygonShape(self.selectedpolygon2, pos)
                self.movingShape = True
                self.shapeMoved.emit()
                self.repaint()
            elif self.selectedpolygon and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMovepolygonShape(self.selectedpolygon, pos)
                self.movingShape = True
                self.shapeMoved.emit()
                self.repaint()
          
                    

        # Just hovering over the canvas, 2 posibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        # self.("Image")
        for polygon in reversed([s for s in self.polygons if self.isVisible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            if self.selectedpolygon:
                if self.polygonEditing() and self.selectedpolygon.innerpolygons != []:
                    for inpolygon in reversed([s for s in self.selectedpolygon.innerpolygons if self.isVisible(self.selectedpolygon)]):
                        if self.selectedpolygon2:
                            index = self.selectedpolygon2.nearestVertex(pos, self.epsilon)
                            index_edge = self.selectedpolygon2.nearestEdge(pos, self.epsilon)
                            if index is not None:
                                selecting2 = True
                            else:
                                index = inpolygon.nearestVertex(pos, self.epsilon)
                            innerpolygon = inpolygon
                            break
                        else:
                            index = inpolygon.nearestVertex(pos, self.epsilon)
                            index_edge = inpolygon.nearestEdge(pos, self.epsilon)
                            innerpolygon = inpolygon
                            if index != None:
                                break

                else:
                    index = self.selectedpolygon.nearestVertex(pos, self.epsilon)
                    index_edge = self.selectedpolygon.nearestEdge(pos, self.epsilon)
                    if index is not None:
                        selecting = True
                    else:
                        index = polygon.nearestVertex(pos, self.epsilon)
            else:
                index = polygon.nearestVertex(pos, self.epsilon)
                index_edge = polygon.nearestEdge(pos, self.epsilon)
            if index is not None:
                if self.selectedpolygonVertex():
                    if self.hpolygon:
                        self.hpolygon.highlightClear()
                if self.polygonEditing():        
                    if selecting2:
                        self.hpolygonVertex, self.hpolygon, self.hpolygonedge = index, self.selectedpolygon2,index_edge
                        self.selectedpolygon2.highlightVertex(index, self.selectedpolygon2.MOVE_VERTEX)
                    else:
                        self.hpolygonVertex, self.hpolygon, self.hpolygonedge = index, innerpolygon,index_edge
                        if innerpolygon:
                            innerpolygon.highlightVertex(index, innerpolygon.MOVE_VERTEX)
                elif selecting:
                    self.hpolygonVertex, self.hpolygon, self.hpolygonedge = index, self.selectedpolygon,index_edge
                    self.selectedpolygon.highlightVertex(index, polygon.MOVE_VERTEX)
                else:
                    self.hpolygonVertex, self.hpolygon, self.hpolygonedge = index, polygon,index_edge
                    polygon.highlightVertex(index, polygon.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip("Click & drag to move point")
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif self.polygonEditing() and self.selectedpolygon:
                if self.selectedpolygon.innerpolygons != []:
                    for polygon in self.selectedpolygon.innerpolygons:
                        if polygon.containsPoint(pos):
                            
                            if self.selectedpolygonVertex():
                                self.hpolygon.highlightClear()
                            self.hpolygonVertex = None
                            self.hpolygon = polygon
                            self.hpolygonedge = index_edge
                            self.setToolTip(
                                "Click & drag to move shape '%s'" )
                            self.setStatusTip(self.toolTip())
                            self.overrideCursor(CURSOR_GRAB)
                            self.update()
                            break
            elif polygon.containsPoint(pos):
                if self.selectedpolygonVertex():
                    self.hpolygon.highlightClear()
                self.hpolygonVertex = None
                self.hpolygon = polygon
                self.hpolygonedge = index_edge
                self.setToolTip(
                    "Click & drag to move shape '%s'" )
                self.setStatusTip(self.toolTip())
                self.overrideCursor(CURSOR_GRAB)
                self.update()
                break
            else:  # Nothing found, clear highlights, reset state.
                if self.hpolygon:
                    self.hpolygon.highlightClear()
                    self.update()
                if not self.selectedpolygon:
                    self.hpolygon = None
                self.hpolygonVertex,  self.hpolygonedge = None, None
                self.setToolTip('('+str(int(pos.x()))+'['+str(int(pos.x())+176)+'],'+str(int(pos.y()))+')')
        if not self.outOfPixmap(pos):
            self.setToolTip('('+str(int(pos.x()))+'['+str(int(pos.x())+176)+'],'+str(int(pos.y()))+')')
            self.repaint()

    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.pos())
        if ev.button() == Qt.LeftButton:
            if self.drawing() or self.polygonDrawing():
                if self.polcurrent:
                    # Add point to existing shape.
                    if self.createMode == 'polygon':
                        self.polcurrent.addPoint(self.polline[1])
                        self.polline[0] = self.polcurrent[-1]
                        if self.polcurrent.isClosed():
                            self.polfinalise()
                            if not self.polygonDrawing():
                                self.newShape.emit()
                    elif self.createMode in ['rectangle', 'circle', 'line']:
                        assert len(self.polcurrent.points) == 1
                        if self.createMode == 'rectangle':
                            self.polcurrent.points = self.getrectanglepoints(self.polline.points)
                        else:
                            self.polcurrent.points = self.polline.points
                        self.polfinalise()
                        if not self.polygonDrawing():
                            self.newShape.emit()
                    elif self.createMode == 'linestrip':
                        self.polcurrent.addPoint(self.polline[1])
                        self.polline[0] = self.polcurrent[-1]
                        if int(ev.modifiers()) == QtCore.Qt.ControlModifier:
                            self.polfinalise()
                            if not self.polygonDrawing():
                                self.newShape.emit()
                    elif self.createMode == 'x-rectangle':
                        if len(self.polcurrent.points) < 2:
                            self.polcurrent.addPoint(self.polline[1])
                            self.polline[0] = self.polcurrent[-1]
                        elif len(self.polcurrent.points) >= 2:
                            self.polfinalise()
                            if not self.polygonDrawing():
                                self.newShape.emit()
                elif not self.outOfPixmap(pos):
                    # Create new shape.
                    self.polcurrent = Polygon(shape_type=self.createMode,line_color=self.pollineColor)
                    self.polcurrent.addPoint(pos)
                    if self.createMode == 'point':
                        self.polfinalise()
                        if not self.polygonDrawing():
                            self.newShape.emit()
                    else:
                        if self.createMode == 'circle':
                            self.polcurrent.shape_type = 'circle'
                        self.polline.points = [pos, pos]
                        self.setHiding()
                        self.drawingPolygon.emit(True)
                        self.update()
            
            else:
                
                self.selectpolygonPoint(pos)
                self.prevPoint = pos
                self.repaint()
            
        elif ev.button() == Qt.RightButton and self.drawing():
            if self.polcurrent:
                if self.polcurrent.shape_type not in ['circle','rectangle','line']:
                    self.polcurrent.points.pop(-1)
                    self.repaint()
        elif ev.button() == Qt.RightButton:
            if self.polygonEditing() and self.selectedpolygon2:
                if self.selectedpolygon2.shape_type not in ['circle','rectangle','line']:
                    index = self.selectedpolygon2.nearestVertex(pos, self.epsilon)
                    if index is not None:
                        del self.selectedpolygon2.points[index]
                        if self.selectedpolygon2.points == []:
                            self.selectedpolygon.innerpolygons.remove(self.selectedpolygon2)
                        self.shapeMoved.emit()
                        self.repaint()
            elif self.selectedpolygon:
                if self.selectedpolygon.shape_type not in ['circle','rectangle','line']:
                    index = self.selectedpolygon.nearestVertex(pos, self.epsilon)
                    if index is not None:
                        del self.selectedpolygon.points[index]
                        if self.selectedpolygon.points == []:
                            self.polygons.remove(self.selectedpolygon)
                        self.shapeMoved.emit()
                        self.repaint()
            self.prevPoint = pos
        elif ev.button() == Qt.MidButton and self.drawing():
            if self.createMode == 'linestrip':
                self.polfinalise()
                self.newShape.emit()
        elif ev.button() == Qt.MidButton:
            if self.polygonEditing() and self.selectedpolygon2:
                if self.selectedpolygon2.shape_type not in ['circle','rectangle','point','line']:
                    index = self.selectedpolygon2.nearest1Edge(pos)
                    self.selectedpolygon2.points.insert(index,pos)
                    self.shapeMoved.emit()
                    self.repaint()
            elif self.selectedpolygon:
                if self.selectedpolygon.shape_type not in ['circle','rectangle','point','line']:
                    index = self.selectedpolygon.nearest1Edge(pos)
                    self.selectedpolygon.points.insert(index,pos)
                    self.shapeMoved.emit()
                    self.repaint()

        


    def mouseReleaseEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton and not self.drawing() and not self.polygonEditing() and not (self.selectedpolygon and self.hpolygonVertex):
            menu = self.menus[bool(self.selectedShapeCopy)]
            self.restoreCursor()
            if not menu.exec_(self.mapToGlobal(ev.pos()))\
               and self.selectedShapeCopy:
                # Cancel the move by deleting the shadow copy.
                self.selectedShapeCopy = None
                self.repaint()
        elif ev.button() == QtCore.Qt.LeftButton and self.selectedShape:
            self.overrideCursor(CURSOR_GRAB)

    def endMove(self, copy=False):
        assert self.selectedpolygon and self.selectedShapeCopy
        shape = self.selectedShapeCopy
        #del shape.fill_color
        #del shape.line_color
        if copy:
            self.polygons.append(shape)
            self.selectedpolygon.selected = False
            self.selectedpolygon = shape
            self.repaint()
        else:
            self.selectedpolygon.points = [p for p in shape.points]
        self.selectedShapeCopy = None

    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selectedpolygon:
            # Only hide other shapes if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.repaint()

    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):
        return self.drawing() and self.current and len(self.current) > 2

    def mouseDoubleClickEvent(self, ev):
        # We need at least 4 points here, since the mousePress handler
        # adds an extra one before this handler is called.
        if self.canCloseShape() and len(self.current) > 3:
            self.current.popPoint()
            self.finalise()


    def calculateOffsets(self, shape, point):
        rect = shape.boundingRect()
        x1 = rect.x() - point.x()
        y1 = rect.y() - point.y()
        x2 = (rect.x() + rect.width()) - point.x()
        y2 = (rect.y() + rect.height()) - point.y()
        self.offsets = QPointF(x1, y1), QPointF(x2, y2)


    def paintEvent(self, event):
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        p.drawPixmap(0, 0, self.pixmap)
        Shape.scale = self.scale
        for polygon in self.polygons:
            if self.isVisible(polygon):
                polygon.paint(p)


        if self.polcurrent:
            self.polcurrent.paint(p)
            if not self.polcurrent.shape_type == 'x-rectangle' or not len(self.polcurrent.points)==4:
                self.polline.paint(p)
            else:
                pass

        if self.selectedShapeCopy:
            self.selectedShapeCopy.paint(p)

        



        if self.polcurrent:
            
            if self.createMode == 'line':
                try:
                    x1,y1,x1_p,y1_p = self.getLine(self.polcurrent,self.prevPoint)
                    p.drawLine(self.prevPoint.x(),self.prevPoint.y(), 2*self.prevPoint.x()-self.polcurrent[-1].x(),2*self.prevPoint.y()-self.polcurrent[-1].y())
                    p.drawLine(self.prevPoint.x()+x1, self.prevPoint.y()+y1, self.prevPoint.x()-x1,self.prevPoint.y()-y1 )
                    # if x1_p != None:
                    #     p.drawLine(self.polcurrent[-1].x(), self.polcurrent[-1].y(), x1_p, y1_p)
                except Exception as e:
                    print(e.args)
            elif self.drawing() and not self.prevPoint.isNull() and not self.outOfPixmap(self.prevPoint):
                if self.createMode == 'x-rectangle':
                    pass
                else:
                    p.setPen(QColor(0, 0, 0))
                    p.drawLine(self.prevPoint.x(), 0, self.prevPoint.x(), self.pixmap.height())
                    p.drawLine(0, self.prevPoint.y(), self.pixmap.width(), self.prevPoint.y())
            self.polcurrent.paint(p)
            self.polline.paint(p)


        self.setAutoFillBackground(True)
        if self.verified == 'yes':
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(184, 239, 38, 128))
            self.setPalette(pal)
        elif self.verified == 'yes1':
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(238, 44, 44, 128))
            self.setPalette(pal)
        elif self.verified == 'yes2':
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(0, 0, 255, 128))
            self.setPalette(pal)
        else:
            pal = self.palette()
            pal.setColor(self.backgroundRole(), QColor(232, 232, 232, 255))
            self.setPalette(pal)

        p.end()

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical coordinates."""
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QPointF(x, y)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w and 0 <= p.y() <= h)

    def closeEnough(self, p1, p2):
        #d = distance(p1 - p2)
        #m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        return distance(p1 - p2) < self.epsilon

    def intersectionPoint(self, p1, p2):
        # Cycle through each image edge in clockwise fashion,
        # and find the one intersecting the current line segment.
        # http://paulbourke.net/geometry/lineline2d/
        size = self.pixmap.size()
        points = [(0, 0),
                  (size.width(), 0),
                  (size.width(), size.height()),
                  (0, size.height())]
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QPointF(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QPointF(min(max(0, x2), max(x3, x4)), y3)
        return QPointF(x, y)

    def intersectingEdges(self, x1y1, x2y2, points):
        """For each edge formed by `points', yield the intersection
        with the line segment `(x1,y1) - (x2,y2)`, if it exists.
        Also return the distance of `(x2,y2)' to the middle of the
        edge along with its index, so that the one closest can be chosen."""
        x1, y1 = x1y1
        x2, y2 = x2y2
        for i in range(4):
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QPointF((x3 + x4) / 2, (y3 + y4) / 2)
                d = distance(m - QPointF(x2, y2))
                yield d, i, (x, y)

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):
        qt_version = 4 if hasattr(ev, "delta") else 5
        if qt_version == 4:
            if ev.orientation() == Qt.Vertical:
                v_delta = ev.delta()
                h_delta = 0
            else:
                h_delta = ev.delta()
                v_delta = 0
        else:
            delta = ev.angleDelta()
            h_delta = delta.x()
            v_delta = delta.y()

        mods = ev.modifiers()
        if Qt.ControlModifier == int(mods) and v_delta:
            self.zoomRequest.emit(v_delta)
        else:
            v_delta and self.scrollRequest.emit(v_delta, Qt.Vertical)
            h_delta and self.scrollRequest.emit(h_delta, Qt.Horizontal)
        ev.accept()

    def keyPressEvent(self, ev):
        key = ev.key()
        if key == Qt.Key_Escape and self.current:
            print('ESC press')
            self.current = None
            self.drawingPolygon.emit(False)
            self.update()
        elif key == Qt.Key_Return and self.canCloseShape():
            self.finalise()
        elif key == Qt.Key_Left and self.selectedpolygon:
            self.moveOnePixel('Left')
        elif key == Qt.Key_Right and self.selectedpolygon:
            self.moveOnePixel('Right')
        elif key == Qt.Key_Up and self.selectedpolygon:
            self.moveOnePixel('Up')
        elif key == Qt.Key_Down and self.selectedpolygon:
            self.moveOnePixel('Down')

        if key == 16777248:
            self.moreselected = True

    def keyReleaseEvent(self, ev):
        key = ev.key()
        if key == 16777248:
            self.moreselected = False

    def moveOnePixel(self, direction):
        # print(self.selectedShape.points)
        if direction == 'Left' and not self.moveOutOfBound(QPointF(-1.0, 0)):
            # print("move Left one pixel")
            for point in self.selectedpolygon.points:
                point += QPointF(-1.0, 0)
        elif direction == 'Right' and not self.moveOutOfBound(QPointF(1.0, 0)):
            # print("move Right one pixel")
            for point in self.selectedpolygon.points:
                point += QPointF(1.0, 0)
        elif direction == 'Up' and not self.moveOutOfBound(QPointF(0, -1.0)):
            # print("move Up one pixel")
            for point in self.selectedpolygon.points:
                point += QPointF(0, -1.0)
        elif direction == 'Down' and not self.moveOutOfBound(QPointF(0, 1.0)):
            # print("move Down one pixel")
            for point in self.selectedpolygon.points:
                point += QPointF(0, 1.0)
        self.shapeMoved.emit()
        self.repaint()

    def copySelectedShape(self):
        if self.selectedpolygon:
            shape = self.selectedpolygon.copy()
            self.deSelectpolygon()
            self.polygons.append(shape)
            shape.selected = True
            self.selectedpolygon = shape
            self.boundedShiftShape(shape)
            return shape

    def moveOutOfBound(self, step):
        points = [p1+p2 for p1, p2 in zip(self.selectedShape.points, [step]*4)]
        return True in map(self.outOfPixmap, points)

    def setLastLabel(self, text, text_pose, text_unique, line_color  = None, fill_color = None):
        assert text
        self.polygons[-1].label = text
        self.polygons[-1].pose = text_pose
        self.polygons[-1].unique = text_unique
        if line_color:
            self.polygons[-1].line_color = line_color
        
        if fill_color:
            self.polygons[-1].fill_color = fill_color

        return self.polygons[-1]

    def setPolygonLabel(self,text):
        if text != None:
            self.polcurrent.label = text

    def boundedShiftShape(self, shape):
        # Try to move in one direction, and if it fails in another.
        # Give up if both fail.
        point = shape[0]
        offset = QPointF(2.0, 2.0)
        self.calculateOffsets(shape, point)
        self.prevPoint = point
        if not self.boundedMovepolygonShape(shape, point - offset):
            self.boundedMovepolygonShape(shape, point + offset)


    def undoLastLine(self):
        assert self.polygons
        self.current = self.polygons.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)

    def resetAllLines(self):
        assert self.polygons
        self.current = self.polygons.pop()
        self.current.setOpen()
        self.line.points = [self.current[-1], self.current[0]]
        self.drawingPolygon.emit(True)
        self.current = None
        self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap):
        self.pixmap = pixmap
        self.shapes = []
        self.repaint()

    def loadShapes(self, shapes):
        self.polygons = list(shapes)
        self.current = None
        self.repaint()

    def setShapeVisible(self, shape, value):
        self.visible[shape] = value
        self.repaint()

    def currentCursor(self):
        cursor = QApplication.overrideCursor()
        if cursor is not None:
            cursor = cursor.shape()
        return cursor

    def overrideCursor(self, cursor):
        self._cursor = cursor
        if self.currentCursor() is None:
            QApplication.setOverrideCursor(cursor)
        else:
            QApplication.changeOverrideCursor(cursor)

    def restoreCursor(self):
        QApplication.restoreOverrideCursor()

    def resetState(self):
        self.restoreCursor()
        self.pixmap = None
        self.update()




    # polygon addtional 

    def squarepoint(self,points,pos):
        dx = points[1].x()-pos.x()
        dy = points[1].y()-pos.y()
        u = (points[0].x()-points[1].x())*dx + (points[0].y()-points[1].y())*dy
        div = dx*dx + dy*dy
        if div == 0:
            div = 1
        u = u/div
        x1 = points[1].x()+u*dx
        y1 = points[1].y()+u*dy
        point1 = QPointF(x1,y1)
        #
        x2 = points[0].x()+points[1].x()-x1
        y2 = points[0].y()+points[1].y()-y1
        point2 = QPointF(x2,y2)
        return point1,point2

    def getLine(self,pointbox,point2):
        
        x1 = pointbox[-1].x()
        y1 = pointbox[-1].y()
        x2 = point2.x()
        y2 = point2.y()
        c = x2 - x1
        d = y2 - y1
        if len(pointbox) <= 1:
            if c <= 0:
                # return x2+d,y2 -c,None,None
                return d, -c ,None,None
            else:
                # return x2-d,y2 +c,None,None
                return -d, c ,None,None
        else:
            if pointbox[-1].x() <= pointbox[-2].x():
                x1_p = pointbox[-1].x()+(pointbox[-1].y() - pointbox[-2].y())
                y1_p = pointbox[-1].y()-(pointbox[-1].x() - pointbox[-2].x())
            else:
                x1_p = pointbox[-1].x()-(pointbox[-1].y() - pointbox[-2].y())
                y1_p = pointbox[-1].y()+(pointbox[-1].x() - pointbox[-2].x())
            c_p = x1_p - pointbox[-1].x()
            d_p = y1_p - pointbox[-1].y()
            if abs(d/c) > abs(d_p/c_p):
                return d,-c,x1_p,y1_p
            else:
                return -d,c,x1_p,y1_p

    def rotatepoint(self,point1,point2,point3,targetpoint1,check):
        div1 = (point2.x() - point1.x())
        div2 = (point3.x() - point1.x())
        if div1 == 0:
            div1 = 0.001
        if div2 == 0:
            div2 = 0.001
        
        
        iniangle = math.atan((point2.y() - point1.y())/div1)
        newangle = math.atan((point3.y() - point1.y())/div2)
        d_angle = newangle - iniangle
        if point3.x() < point1.x() and check==0:
            d_angle = d_angle - math.pi
        if point3.x() > point1.x() and check==1:
            d_angle = d_angle - math.pi
        cosd = math.cos(d_angle)
        sind = math.sin(d_angle)
        
        pointx = (targetpoint1.x()-point1.x())*cosd - (targetpoint1.y()-point1.y())*sind + point1.x()
        pointy = (targetpoint1.x()-point1.x())*sind + (targetpoint1.y()-point1.y())*cosd + point1.y()

        targetpoint2 = QPointF(pointx,pointy)
        # print('------------')
        # print(targetpoint1)
        # print('#########')
        # print(targetpoint2)
        # print('------------')
        return targetpoint2
        


    def deleteSelected(self):
        if self.selectedpolygon2:
            shape = self.selectedpolygon2
            self.selectedpolygon.innerpolygons.remove(self.selectedpolygon2)
            self.selectedpolygon2 = None
            self.update()
            return shape , 0
        elif self.selectedpolygon:
            shape = self.selectedpolygon
            self.polygons.remove(self.selectedpolygon)
            self.selectedpolygon = None
            self.update()
            return shape , 1

    def getrectanglepoints(self,points):
        newpoints = []
        newpoints.append(points[0])
        newpoints.append(QPointF(points[1].x(),points[0].y()))
        newpoints.append(points[1])
        newpoints.append(QPointF(points[0].x(),points[1].y()))
        return newpoints


    def polfinalise(self):
        assert self.polcurrent
        self.polcurrent.close()
        self.polshapes.append(self.polcurrent)
        self.storeShapes()
        if self.drawing():
            self.polygons.append(self.polcurrent)
        elif self.polygonDrawing() and self.selectedpolygon:
            self.selectedpolygon.innerpolygons.append(self.polcurrent)
        self.polcurrent = None
        self.update()

    def storeShapes(self):
        shapesBackup = []
        for shape in self.polshapes:
            shapesBackup.append(shape.copy())
        if len(self.shapesBackups) >= 10:
            self.shapesBackups = self.shapesBackups[-9:]
        self.shapesBackups.append(shapesBackup)

    def polcloseEnough(self, p1, p2):
        #d = distance(p1 - p2)
        #m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        return distance(p1 - p2) < self.polepsilon

    
    def selectShape(self, polygon):
        self.deSelectpolygon()
        polygon.selected = True
        if self.polygonEditing():
            self.selectedpolygon2 = polygon
        else:
            self.selectedpolygon = polygon
        self.setHiding()
        if not self.polygonEditing():
            self.selectionChanged.emit(True)
        self.update()

    def selectpolygonPoint(self, point):
        """Select the first polygon created which contains this point."""
        
        if not self.selectedpolygon or not (self.hpolygonVertex!=None):
            self.deSelectpolygon()
        if self.selectedpolygonVertex():  # A vertex is marked for selection.
            index, polygon = self.hVertex, self.hpolygon
            polygon.highlightVertex(index, polygon.MOVE_VERTEX)
            self.selectShape(polygon)
            return
        if self.polygonDrawing() or self.polygonEditing():
            if self.polcurrent and self.polygonDrawing():
                pass
            elif self.selectedpolygon and self.polygonEditing():
                for polygon in reversed(self.selectedpolygon.innerpolygons):
                    if polygon.containsPoint(point):
                        polygon.selected = True
                        self.selectedpolygon2 = polygon
                        self.calculateOffsets(polygon, point)
                        self.setHiding()
                        self.update()
                        return
        else:
            for polygon in reversed(self.polygons):
                if self.isVisible(polygon) and polygon.containsPoint(point):
                    polygon.selected = True
                    self.selectedpolygon = polygon
                    self.calculateOffsets(polygon, point)
                    self.setHiding()
                    self.selectionChanged.emit(True)
                    self.update()
                    return

    
    def deSelectpolygon(self):
        if self.selectedpolygon2 and self.polygonEditing():
            self.selectedpolygon2.selected = False
            self.selectedpolygon2 = None
            self.setHiding(False)
            self.update()
        elif self.selectedpolygon and not self.polygonEditing():
            if self.selectedpolygon2:
                self.selectedpolygon2.selected = False
                self.selectedpolygon2.highlightClear()
                self.selectedpolygon2 = None
            self.selectedpolygon.selected = False
            self.selectedpolygon.highlightClear()
            self.selectedpolygon = None
            self.setHiding(False)
            self.selectionChanged.emit(False)
            self.update()
    

    def selectedpolygonVertex(self):
        return self.hpolygonVertex is not None


    def boundedMovepolygonVertex(self, pos):
        index, shape = self.hpolygonVertex, self.hpolygon
        point = shape[index]
        if self.outOfPixmap(pos):
            pos = self.intersectionPoint(point, pos)
        shape.moveVertexBy(index, pos - point)

    def boundedMoverectangleVertex(self, pos):
        index, shape = self.hpolygonVertex, self.hpolygon
        point = shape.points[index]
        if self.outOfPixmap(pos):
            pos = self.intersectionPoint(point, pos)
        shiftPos = pos - point
        shape.moveVertexBy(index, shiftPos)
        lindex = (index + 1) % 4
        rindex = (index + 3) % 4
        lshift = None
        rshift = None
        if index % 2 == 0:
            rshift = QPointF(shiftPos.x(), 0)
            lshift = QPointF(0, shiftPos.y())
        else:
            lshift = QPointF(shiftPos.x(), 0)
            rshift = QPointF(0, shiftPos.y())
        shape.moveVertexBy(rindex, rshift)
        shape.moveVertexBy(lindex, lshift)
        # shape.points = self.rectanglepointsresize(shape)

    def boundedMoveXrectangleVertex(self,pos):
        index, shape = self.hpolygonVertex, self.hpolygon
        if index == 1 or index == 3:
            points = (shape.points[index-3],shape.points[index-1])
            point1,point2 = self.squarepoint(points,pos)
            shape.points[index] = point1
            shape.points[index-2] = point2
        elif index == 0 or index == 2:
            scale = labelme.utils.distance(pos-self.tempbox[index-2])/labelme.utils.distance(self.tempbox[index]-self.tempbox[index-2])
            if index == 0:
                check = 1
            else:
                check = 0
            newpoint1x = self.tempbox[index-2].x() - (scale*(self.tempbox[index-2].x()-self.tempbox[index-1].x()))
            newpoint1y = self.tempbox[index-2].y() + (scale*(self.tempbox[index-1].y()-self.tempbox[index-2].y()))
            newpoint1 = QPointF(newpoint1x,newpoint1y)
            newpoint2x = self.tempbox[index-2].x() - (scale*(self.tempbox[index-2].x()-self.tempbox[index-3].x()))
            newpoint2y = self.tempbox[index-2].y() + (scale*(self.tempbox[index-3].y()-self.tempbox[index-2].y()))
            newpoint2 = QPointF(newpoint2x,newpoint2y)
            
            shape.points[index-1] = self.rotatepoint(self.tempbox[index-2],self.tempbox[index],pos,newpoint1,check)
            shape.points[index-3] = self.rotatepoint(self.tempbox[index-2],self.tempbox[index],pos,newpoint2,check)
            
            shape.points[index] = pos
            

            

    def rectanglepointsresize(self,polygon):
        newpointbox = [QPointF(0,0),QPointF(0,0),QPointF(0,0),QPointF(0,0)]
        xpoint = []
        ypoint = []
        for point in polygon.points:
            xpoint.append(point.x())
            ypoint.append(point.y())
        for point in polygon.points:
            if point.x() == min(xpoint) and point.y() == min(ypoint):
                newpointbox[0] = point
            elif point.x() == max(xpoint) and point.y() == min(ypoint):
                newpointbox[1] = point
            elif point.x() == max(xpoint) and point.y() == max(ypoint):
                newpointbox[2] = point
            elif point.x() == min(xpoint) and point.y() == max(ypoint):
                newpointbox[3] = point
        return newpointbox





    def boundedMovepolygonShape(self, shape, pos):
        if self.outOfPixmap(pos):
            return False  # No need to move
        
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QtCore.QPoint(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QtCore.QPoint(min(0, self.pixmap.width() - o2.x()-2),
                                 min(0, self.pixmap.height() - o2.y())-2)
        # XXX: The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason.
        # 
        dp = pos - self.prevPoint
        if dp:
            shape.moveBy(dp)
            self.prevPoint = pos
            return True
        return False


#dist1 = labelme.utils.distance(point1-points[1])
        # dist2 = labelme.utils.distance(points[0]-point1)
        # if dist1 == 0:
        #     dist1 = 1
        # x2 = points[1].x()-(points[1].y()-y1)*(dist2/dist1)
        # y2 = points[1].y()-(x1-points[1].x())*(dist2/dist1)
        # point2 = QPointF(x2,y2)
        # print(x1,y1)
        # # print(point1)
        # # print(point2)
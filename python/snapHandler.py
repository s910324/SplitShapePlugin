import pya
import math
import misc
from typing import Union, Dict, List
from   enum import IntEnum
import markerTheme as mkThm

# V20230923

class SnapPolicy(IntEnum):
    showSearchRange = 0b000001
    snapCenter      = 0b000010
    snapVertex      = 0b000100
    snapEdge        = 0b001000
    snapEdgeCenter  = 0b010000
    snapDefault     = 0b001110
    
class SnapHandler:
    def __init__(self, view : pya.LayoutView, snapPolicy : SnapPolicy = SnapPolicy.snapDefault):
        self.view            = view
        self.markPropList    = []
        self.activeMarkers   = []
        self.setSnapPolicy(snapPolicy)
        
    def setSnapPolicy(self, snapPolicy : SnapPolicy):
        self.snapPolicy      = snapPolicy
        self.showSearchRange = (snapPolicy & SnapPolicy.showSearchRange) > 0
        self.snapCenter      = (snapPolicy & SnapPolicy.snapCenter)      > 0
        self.snapVertex      = (snapPolicy & SnapPolicy.snapVertex)      > 0
        self.snapEdge        = (snapPolicy & SnapPolicy.snapEdge)        > 0
        self.snapEdgeCenter  = (snapPolicy & SnapPolicy.snapEdgeCenter)  > 0       

    def clearMarkers(self):
        for marker in self.activeMarkers:
            marker._destroy()
            
        self.markPropList  = []
        self.activeMarkers = []

    def updateMarkers(self):
        for marker in self.activeMarkers:
            marker._destroy()
        self.activeMarkers = []

        for markProp in self.markPropList:
            marker = pya.Marker(self.view)
            marker.set(markProp["data"])
            marker.line_width  = markProp["theme"]["line_width"]
            marker.line_style  = markProp["theme"]["line_style"] 
            marker.vertex_size = markProp["theme"]["vertex_size"] 
            self.activeMarkers.append(marker)
        self.markPropList = []

    def cursorMark(self, p : pya.DPoint ):
        crossLength = misc.dPixelLength(self.view, 20)
        return mkThm.cursorMark(p, crossLength)

        
    def detectRangeMark(self, p : pya.DPoint, detectRange : Union[int, float]):
        return mkThm.detectRangeMark(p, detectRange)
             
    def centerMark(self, shape : pya.DPolygon):
        crossLength = misc.dPixelLength(self.view, 5)
        return mkThm.centerMark(shape, crossLength)
        
    def edgeMark(self, edge : pya.DEdge):
        arrowLength = misc.dPixelLength(self.view, 20)
        direction   = 1
        return mkThm.edgeArrowMark(edge, arrowLength, direction)
        
    def edgeCenterMark(self, edge : pya.DEdge):
        markLength  = misc.dPixelLength(self.view, 20)
        return mkThm.edgeCenterMark(edge, markLength)
                
    def vertexMark(self, p : pya.DPoint):
        crossLength = misc.dPixelLength(self.view, 20)
        return mkThm.vertexMark(p, crossLength)
        
    def vertexInRange(self, point : pya.DPoint, vertex : pya.DPoint, detectRange : Union[int, float]):
        inXRange   = (vertex.x - detectRange) <= point.x <= (vertex.x + detectRange)
        inYRange   = (vertex.y - detectRange) <= point.y <= (vertex.y + detectRange)
        detected   = all([inXRange, inYRange])
        return detected
        
    def edgeInRange(self, point : pya.DPoint, edge : pya.DEdge, detectRange : Union[int, float]):
        detectArea = pya.DPath([edge.p1, edge.p2], detectRange * 2, detectRange, detectRange).simple_polygon()
        detected   = detectArea.inside(point)
        return detected
    
    def visibleLayers(self):
        result = []
        itr = self.view.begin_layers()
        while not itr.at_end():
            lyp = itr.current()
            if lyp.visible: result.append(lyp.layer_index())
            itr.next()
        return result
 
    def shapeInRange(self, rangeDBox : pya.DBox, layerIDList : List[int]):
        result        = []
        cellView      = self.view.active_cellview()
        unit          = cellView.layout().dbu
        cell          = cellView.cell
        visibleLayers = self.visibleLayers()
        
        for li in layerIDList:
            for o in cell.begin_shapes_rec_touching(li, rangeDBox):
                if (o.shape().polygon):
                    result.append(o.shape().polygon.transformed(o.trans()).to_dtype(unit))
        return result
        
    def shapeInVisibleRange(self, rangeDBox : pya.DBox):
        return self.shapeInRange(rangeDBox, self.visibleLayers())

    def snapPoint(self, point : pya.DPoint, edge_point : Union[pya.DEdge, pya.DPoint]): 
        if isinstance(edge_point, pya.DEdge):
            edge = edge_point
            dx   = edge.p2.x - edge.p1.x 
            dy   = edge.p2.y - edge.p1.y 
            if dx == 0:
                return pya.DPoint(edge.p1.x, point.y)
            if dy == 0:
                return pya.DPoint(point.x, edge.p1.y)
            else:
                return pya.DPoint(point.x,(point.x - edge.p1.x)/dx * dy + edge.p1.y)
        if isinstance(edge_point, pya.DPoint):
            return edge_point       
        return point

    def markPropsAppend(self, markProps):
        if isinstance(markProps, dict):
            self.markPropList.append(markProps)
        elif isinstance(markProps, list):
            for markProp in markProps:
                self.markPropsAppend(markProp)
                
                 
    def snapToObject(self, p : pya.DPoint, detectRange : Union[int, float], hoverShapes : List[pya.DPolygon]):
        cell             = self.view.active_cellview().cell
        minDistance      = detectRange
        ranegDVector     = pya.DVector(detectRange, detectRange)
        rangeDBox        = pya.DBox(p - ranegDVector, p + ranegDVector)
        centerShapes     = sorted(hoverShapes, key = lambda hoveredShape: hoveredShape.bbox().center().distance(p))[0:10] if self.snapCenter else []
        hlVertex         = None
        hlEdge           = None
        hlCenter         = None
        snapPoint        = p
        
        self.markPropsAppend([self.centerMark(centerShape) for centerShape in centerShapes])
        
        for hoveredShape in hoverShapes:
               
            for e in hoveredShape.each_edge():
                if self.edgeInRange(p, e, detectRange):
                    epDistance  = e.distance_abs(p)

                    if epDistance <= minDistance:
                        minDistance = epDistance
                        snapPoint   = self.snapPoint(p, e) if self.snapEdge else p
                        hlEdge      = e                    if self.snapEdge else hlEdge
                        
                        ppc         = pya.DPoint((e.p1.x + e.p2.x)/2, (e.p1.y + e.p2.y)/2)
                        pointDists  = [
                            {"point" : e.p1, "distance" : e.p1.distance(p)},
                            {"point" : e.p2, "distance" : e.p2.distance(p)},
                            {"point" : ppc,  "distance" : ppc.distance(p)},
                        ]
                        pointDists = pointDists if self.snapEdgeCenter else pointDists[0:2]
                        pointDist  = sorted(pointDists, key = lambda pd : pd["distance"])[0]
                        ppDistance = pointDist["distance"]
                        hlVertex   = None
                        
                        if (ppDistance < (minDistance * 2)):
                            v = pointDist["point"]
                            if self.vertexInRange(p, v, detectRange):
                                snapPoint   = self.snapPoint(p, v) if self.snapVertex else p
                                hlVertex    = v                    if self.snapVertex else hlVertex

            center = hoveredShape.bbox().center()
            if self.vertexInRange(p, center, detectRange):
                cpDistance = center.distance(p)
                if (cpDistance < (minDistance * 2)):
                    snapPoint = self.snapPoint(p, center) if self.snapCenter else p
                    hlCenter  = center                    if self.snapVertex else hlCenter

        if hlCenter:
            self.markPropsAppend(self.cursorMark(snapPoint))
            
        else:
        
            if hlEdge: 
                self.markPropsAppend(self.edgeMark(hlEdge))
                
                if self.snapEdgeCenter:
                    self.markPropsAppend(self.edgeCenterMark(hlEdge))
            
            if hlVertex:
                self.markPropsAppend(self.vertexMark(hlVertex))
                
            else:
                self.markPropsAppend(self.cursorMark(snapPoint))
             
        if self.showSearchRange:
            self.markPropsAppend(self.detectRangeMark(p, detectRange))                                                    

        return snapPoint
    

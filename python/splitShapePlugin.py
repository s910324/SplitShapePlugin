import pya
import math
import functools
import snapHandler 

class SplitShapePlugin(pya.Plugin):
    def __init__(self, view):
        super(SplitShapePlugin, self).__init__()
        self.view            = view
        self.cellView        = None
        self.cell            = None
        self.unit            = None
        self.activeMarkers   = []
        self.markPropList    = []

        self.centerSnap      = False
        self.directions      = ["V", "H", "VH", "LS", "RS"]
        self.cutDirection    = self.directions[0]
        self.snappedPoint    = None
        self.withSelected    = False
        self.selectedObjs    = []
        self.selectedObjBox  = None

        self.snapHandler     = snapHandler.SnapHandler(self.view, showSearchRange = False)

        
    def validateView(self, view):
        if not(view):
            self.deactive()
        
        
    def activated(self):
        self.validselect()

    def deactivated(self):
        self.clearAllMarker()
        self.ungrab_mouse()

    def deactive(self):
        esc_key  = 16777216 
        keyPress = pya.QKeyEvent(pya.QKeyEvent.KeyPress, esc_key, pya.Qt.NoModifier)
        pya.QApplication.sendEvent(self.view.widget(), keyPress)        

    def validselect(self):
        self.cellView     = self.view.active_cellview()
        self.cell         = self.cellView.cell
        self.unit         = self.cellView.layout().dbu
        unit              = self.view.active_cellview().layout().dbu
        self.selectedObjs = [o for o in self.view.each_object_selected() if not(o.is_cell_inst())]
        self.withSelected = False
        
        if self.selectedObjs:
            boxList             = [o.shape.polygon.transformed(o.trans()).to_dtype(unit).bbox() for o in self.selectedObjs]
            self.selectedObjBox = functools.reduce(lambda a, b: a+b, boxList)
            self.withSelected   = True

            
    def clearAllMarker(self):
        self.clearMarkers()
        self.snapHandler.clearMarkers()

    def updateAllMarker(self):
        self.updateMarkers()
        self.snapHandler.updateMarkers()
                
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
            
    def mouse_click_event(self, p, buttons, prio):
        if prio:
            if buttons in [8]:
                self.view.transaction("slice Shape")
                try:
                    for o in [o.dup() for o in self.selectedObjs]:
                        shape    = o.shape
                        out_reg  = pya.Region()
                        poly_reg = pya.Region(shape.polygon.transformed(o.trans())) 
                        
                        for box in self.cut_box(self.snappedPoint, centerSnap = self.centerSnap):
                            mask_reg = pya.Region(box.to_itype(self.unit))
                            cut_reg  = poly_reg & mask_reg
                            out_reg += cut_reg
       
                        self.cell.shapes(shape.layer).insert(out_reg)
                    
                    for o in self.selectedObjs:
                        try:
                            o.shape.delete()
                        except:
                            pass
                    
                finally:
                    self.view.commit()              
                self.deactive()
                
            if buttons in [16, 32]:
                nextIndex         = (self.directions.index(self.cutDirection) + 1 ) % len(self.directions)
                self.cutDirection = self.directions[nextIndex]
                self.mouse_moved_event(p, buttons, prio)

            return True
        return False

    def mouse_moved_event(self, p, buttons, prio):
        if prio:
            if self.withSelected:
                rangeDBox         = self.selectedObjBox
                searchRange       = min([rangeDBox.width(), rangeDBox.height()]) * 0.1
                self.snappedPoint = self.snapHandler.snapToObject(p, searchRange)
                self.markPropList = self.updateCutEdge(self.snappedPoint, self.selectedObjBox, self.cutDirection, self.centerSnap)
            else:
                tip = '\n\tSelect Shapes before activate plugin\t\n'
                pya.QToolTip().showText( pya.QCursor.pos, tip) 
                self.deactive()
            self.updateAllMarker()
            
            return True
        return False

    def key_event(self, key, buttons):
        if buttons == 2:
            self.centerSnap = not(self.centerSnap)

    def cut_box(self, p, centerSnap = False):
        p1     = self.selectedObjBox.p1
        p2     = self.selectedObjBox.p2
        w      = self.selectedObjBox.width()
        h      = self.selectedObjBox.height()
        c      = self.selectedObjBox.center()
        p      = c if centerSnap else p

        xbound = p.x if (p1.x <= p.x <= p2.x) else sorted([p1.x , p.x , p2.x])[1]
        ybound = p.y if (p1.y <= p.y <= p2.y) else sorted([p1.y , p.y , p2.y])[1]
        p      = pya.DPoint(xbound, ybound)
        
        vCutBoxL = pya.DBox(
            pya.DPoint(  p1.x, p1.y), 
            pya.DPoint(xbound, p2.y)
        )
        
        vCutBoxR = pya.DBox(
            pya.DPoint(xbound, p1.y), 
            pya.DPoint(  p2.x, p2.y)
        )
        
        hCutBoxT = pya.DBox(
            pya.DPoint(p1.x,   p2.y), 
            pya.DPoint(p2.x, ybound)
        )
        
        hCutBoxB = pya.DBox(
            pya.DPoint(p1.x,   p1.y), 
            pya.DPoint(p2.x, ybound)
        )
        
        lsCutBoxL= pya.DPolygon([
            pya.DPoint(p1.x - h, p1.y), 
            pya.DPoint(p1.x - h, p2.y), 
            pya.DPoint(p.x + (p2.y -  p.y), p2.y),
            pya.DPoint(p.x - (p.y  - p1.y), p1.y),
            pya.DPoint(p1.x - h, p1.y)
        ])     
        
        lsCutBoxR= pya.DPolygon([
            pya.DPoint(p2.x + h, p1.y), 
            pya.DPoint(p2.x + h, p2.y), 
            pya.DPoint(p.x + (p2.y -  p.y), p2.y),
            pya.DPoint(p.x - (p.y  - p1.y), p1.y),
            pya.DPoint(p2.x + h, p1.y)
        ])     
               
        rsCutBoxL = pya.DPolygon([
            pya.DPoint(p1.x - h, p1.y), 
            pya.DPoint(p1.x - h, p2.y), 
            pya.DPoint(p.x - (p2.y -  p.y), p2.y), 
            pya.DPoint(p.x + (p.y  - p1.y), p1.y), 
            pya.DPoint(p1.x - h, p1.y) 
        ])          
        
        rsCutBoxR = pya.DPolygon([
            pya.DPoint(p2.x + h, p1.y), 
            pya.DPoint(p2.x + h, p2.y), 
            pya.DPoint(p.x - (p2.y -  p.y), p2.y), 
            pya.DPoint(p.x + (p.y  - p1.y), p1.y), 
            pya.DPoint(p2.x - h, p1.y) 
        ])          
                         
        if self.cutDirection == "V":
            return [vCutBoxL, vCutBoxR]
            
        if self.cutDirection == "H":
            return [hCutBoxT, hCutBoxB]
            
        if self.cutDirection == "VH":
            return [vCutBoxL & hCutBoxB, vCutBoxL & hCutBoxT, vCutBoxR & hCutBoxB, vCutBoxR & hCutBoxT ]

        if self.cutDirection == "LS":
            return [lsCutBoxL, lsCutBoxR ]
            
        if self.cutDirection == "RS":
            return [rsCutBoxL, rsCutBoxR ]

    def updateCutEdge(self, p, dBoundBox, cutDir, centerSnap = False):
        p1, p2, pc     = dBoundBox.p1, dBoundBox.p2, dBoundBox.center()
        xbound, ybound = sorted([p1.x , p.x , p2.x])[1], sorted([p1.y , p.y , p2.y])[1]
        p              =  pc if centerSnap else pya.DPoint(xbound, ybound)
        
        style = lambda edge : self.snapHandler.edgeToArrowPath(edge, 0.01, -1)
        
        theme    = {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        dataDict = { 
            "V"  : [{"data" : style(pya.DEdge(pya.DPoint(xbound, p1.y), pya.DPoint(xbound, p2.y))), "theme" : theme}],
            "H"  : [{"data" : style(pya.DEdge(pya.DPoint(p1.x, ybound), pya.DPoint(p2.x, ybound))), "theme" : theme}],                                 
            "LS" : [{"data" : style(pya.DEdge(pya.DPoint(p.x - (p.y  - p1.y), p1.y), pya.DPoint(p.x + (p2.y -  p.y), p2.y)).clipped(dBoundBox)), "theme" : theme}],
            "RS" : [{"data" : style(pya.DEdge(pya.DPoint(p.x + (p.y  - p1.y), p1.y), pya.DPoint(p.x - (p2.y -  p.y), p2.y)).clipped(dBoundBox)), "theme" : theme}],
            "VH" : [
                {"data" : style(pya.DEdge(pya.DPoint(xbound, p1.y), pya.DPoint(xbound, p2.y))), "theme" : theme},
                {"data" : style(pya.DEdge(pya.DPoint(p1.x, ybound), pya.DPoint(p2.x, ybound))), "theme" : theme}
            ],   
        }
        return dataDict[cutDir]



class SnapHandler(pya.QObject):
    def __init__(self, view, showSearchRange = False, snapCenter = True, snapVertex = True, snapEdge = True):
        super(SnapHandler, self).__init__()
        self.view            = view
        self.cellView        = view.active_cellview()
        self.unit            = self.cellView.layout().dbu
        self.markPropList    = []
        self.activeMarkers   = []

        self.showSearchRange = showSearchRange
        self.snapCenter      = snapCenter
        self.snapVertex      = snapVertex
        self.snapEdge        = snapEdge
        
    def vectorRotate(self, v, angle):
        rad = angle * 0.0174533 
        return pya.DVector(v.x * math.cos(rad) - v.y * math.sin(rad), v.x * math.sin(rad) + v.y * math.cos(rad))

    def displayLength(self, length):
        vp_trans    = self.view.viewport_trans()
        canvasRes   = 1 / max([self.view.viewport_height(), self.view.viewport_width()])
        return length / canvasRes / vp_trans.mag

    def edgeToArrowPath(self, edge, unitLength, direction = 1):
        arrow_length     = self.displayLength(unitLength)
        arrow_width_half = arrow_length * 0.25882 
        arrow_len_vector = (edge.p1 - edge.p2) / edge.length() * arrow_length
        arrow_wid_vector = self.vectorRotate((edge.p1 - edge.p2) / edge.length() * arrow_width_half, 90)
        arrowPath        = pya.DPath ([
            edge.p2,
            edge.p2 + arrow_len_vector * direction - arrow_wid_vector,
            edge.p2 + arrow_len_vector * direction + arrow_wid_vector,
            edge.p2,
            
            edge.p1,
            edge.p1 - arrow_len_vector * direction - arrow_wid_vector,
            edge.p1 - arrow_len_vector * direction + arrow_wid_vector,
            edge.p1,
            ], 0)
        return arrowPath
        
    def setShowSearchRange(self, show):
        self.showSearchRange = show

    def enableSnapCenter(self, snap):
        self.snapCenter = snap

    def enableSnapVertex(self, snap):
        self.snapVertex = snap

    def enableSnapEdge(self, snap):
        self.snapEdge   = snap        

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

    def cursorMark(self, p, detectRange):
        cross_length = self.displayLength(0.01)
        dia1_length  = cross_length / 4
        vx           = pya.DVector(cross_length, 0)
        vy           = pya.DVector(0, cross_length)
        vxy          = pya.DVector(detectRange, detectRange)

        return [{
            "data"  : pya.DPolygon([p + self.vectorRotate(pya.DVector(dia1_length, 0), 360/32 * i) for i in range(33)]), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        },{
            "data"  : pya.DEdge(p + vy, p - vy), 
            "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
        },{
            "data"  : pya.DEdge(p + vx, p - vx), 
            "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
        },{
            "data"  : pya.DBox(p - vxy, p + vxy), 
            "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
        }][0:3 if self.showSearchRange else -1]
           
             
    def centerMark(self, shape):
        c  = shape.bbox().center()
        vl = self.displayLength(0.005)
        vx = pya.DVector(vl, 0)
        vy = pya.DVector(0, vl)
        return [{
            "data"  : pya.DEdge(c + vy, c - vy), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        },{
            "data"  : pya.DEdge(c + vx, c - vx), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        }]
        
    def edgeMark(self, edge):
        return {
            "data"  : self.edgeToArrowPath(edge, 0.01, 1), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        }    
        
    def vertexMark(self, p):
        cross_length = self.displayLength(0.01)
        dia2_length  = cross_length / 4 * 2
        dia1_length  = cross_length / 4
        
        vx = pya.DVector(cross_length, 0)
        vy = pya.DVector(0, cross_length)
        
        return [{
            "data"  : pya.DPolygon([p + self.vectorRotate(pya.DVector(dia2_length, 0), 360/32 * i) for i in range(33)]), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        },{
            "data"  : pya.DPolygon([p + self.vectorRotate(pya.DVector(dia1_length, 0), 360/32 * i) for i in range(33)]), 
            "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
        },{
            "data"  : pya.DEdge(p + vy, p - vy), 
            "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
        },{
            "data"  : pya.DEdge(p + vx, p - vx), 
            "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
        }]
        
    def vertexInRange(self, point, vertex, detectRange):
        inXRange   = (vertex.x - detectRange) <= point.x <= (vertex.x + detectRange)
        inYRange   = (vertex.y - detectRange) <= point.y <= (vertex.y + detectRange)
        detected   = all([inXRange, inYRange])
        return detected
        
    def edgeInRange(self, point, edge, detectRange):
        detectArea = pya.DPath([edge.p1, edge.p2], detectRange * 2).simple_polygon()
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
    
    def shapeInRange(self, rangeDBox):
        result        = []
        unit          = self.unit
        cell          = self.cellView.cell
        visibleLayers = self.visibleLayers()
        
        for li in visibleLayers:
            for o in cell.begin_shapes_rec_touching(li, rangeDBox):
                if not(o.shape().is_text()):
                    result.append(o.shape().polygon.transformed(o.trans()).to_dtype(unit))
        return result
        
    def snapPoint(self, point, edge_point): 
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
        return None

    def markPropsAppend(self, markProps):
        if isinstance(markProps, dict):
            self.markPropList.append(markProps)
        elif isinstance(markProps, list):
            for markProp in markProps:
                self.markPropsAppend(markProp)
                
    def snapToObject(self, p, searchSize, rangeDBox = None):
        cell             = self.cellView.cell
        minDistance      = searchSize
        rngDVector       = pya.DVector(searchSize, searchSize)
        rangeDBox        = rangeDBox if rangeDBox else pya.DBox(p - rngDVector, p + rngDVector)
        hoverShapes      = self.shapeInRange(rangeDBox) 
        centerShapes     = sorted(hoverShapes, key = lambda hoveredShape: hoveredShape.bbox().center().distance(p))[0:10] if self.snapCenter else []
        hlVertex         = None
        hlEdge           = None
        snapPoint        = p
        
        self.markPropsAppend([self.centerMark(centerShape) for centerShape in centerShapes])
        
        for hoveredShape in hoverShapes:
               
            for e in hoveredShape.each_edge():
                if self.edgeInRange(p, e, searchSize):
                    epDistance  = e.distance_abs(p)
                    pp1Distance = e.p1.distance(p)
                    pp2Distance = e.p2.distance(p)
                    
                    if epDistance <= minDistance:
                        minDistance = epDistance
                        snapPoint   = self.snapPoint(p, e) if self.snapEdge else p
                        hlEdge      = e                    if self.snapEdge else hlEdge
                        
                        ppDistance = min([pp1Distance, pp2Distance])
                        hlVertex   = None
                        if (ppDistance < (minDistance * 2)):
                            v = e.p1 if (pp1Distance < pp2Distance) else e.p2
                            if self.vertexInRange(p, v, searchSize):
                                snapPoint   = self.snapPoint(p, v) if self.snapVertex else p
                                hlVertex    = v                    if self.snapVertex else hlVertex

            center = hoveredShape.bbox().center()
            if self.vertexInRange(p, center, searchSize):
                cpDistance = center.distance(p)
                if (cpDistance < (minDistance * 2)):
                    snapPoint = self.snapPoint(p, center) if self.snapCenter else p
                    hlVertex  = center                    if self.snapVertex else hlVertex

        if hlVertex:
            self.markPropsAppend(self.vertexMark(hlVertex))
        else:
            self.markPropsAppend(self.cursorMark(p, searchSize))
             
        if hlEdge:
            self.markPropsAppend(self.edgeMark(hlEdge))                                                        

        return snapPoint            
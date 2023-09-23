import pya
import math
import misc
import functools
import snapHandler as snHdl
import markerTheme as mkThm  


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
        self.snapHandler     = snHdl.SnapHandler(self.view)
        self.snapHandler.setSnapPolicy(snHdl.SnapPolicy.snapDefault | snHdl.SnapPolicy.snapEdgeCenter)
        
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
        self.selectedObjs = [o for o in self.view.each_object_selected() if (not(o.is_cell_inst()) and (o.shape.polygon))]
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
                searchRange       = misc.dPixelLength(self.view, 25)
                rangeDBox         = pya.DBox(pya.DPoint(p.x - searchRange, p.y - searchRange),pya.DPoint(p.x + searchRange, p.y + searchRange))
                hoverShapes       = self.snapHandler.shapeInVisibleRange(rangeDBox)
                self.snappedPoint = self.snapHandler.snapToObject(p, searchRange, hoverShapes)
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
        arrowLength    = misc.dPixelLength(self.view, 20)
        style          = lambda edge : mkThm.edgeArrowMark(edge, arrowLength, -1)
        dataDict       = { 
            "V"  : style(pya.DEdge(pya.DPoint(xbound, p1.y), pya.DPoint(xbound, p2.y))),
            "H"  : style(pya.DEdge(pya.DPoint(p1.x, ybound), pya.DPoint(p2.x, ybound))),                                 
            "LS" : style(pya.DEdge(pya.DPoint(p.x - (p.y  - p1.y), p1.y), pya.DPoint(p.x + (p2.y -  p.y), p2.y)).clipped(dBoundBox)),
            "RS" : style(pya.DEdge(pya.DPoint(p.x + (p.y  - p1.y), p1.y), pya.DPoint(p.x - (p2.y -  p.y), p2.y)).clipped(dBoundBox)),
            "VH" : style(pya.DEdge(pya.DPoint(xbound, p1.y), pya.DPoint(xbound, p2.y)))+ style(pya.DEdge(pya.DPoint(p1.x, ybound), pya.DPoint(p2.x, ybound)))
        }
        return dataDict[cutDir]
        
if __name__ == "__main__":
    mainWindow = pya.Application.instance().main_window()
    layoutView = mainWindow.current_view()  
    ssp = SplitShapePlugin(layoutView)
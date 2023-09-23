import pya
import math
import misc



def edgeToArrowPath(edge, arrowLength, direction = 1):
    arrowWidthHalf = arrowLength * 0.25882 
    arrowLengthVec = (edge.p1 - edge.p2) / edge.length() * arrowLength
    arrowWidthVec  = misc.vectorRotate((edge.p1 - edge.p2) / edge.length() * arrowWidthHalf, 90)
    arrowPath      = pya.DPath ([
        edge.p2,
        edge.p2 + arrowLengthVec * direction - arrowWidthVec,
        edge.p2 + arrowLengthVec * direction + arrowWidthVec,
        edge.p2,
        
        edge.p1,
        edge.p1 - arrowLengthVec * direction - arrowWidthVec,
        edge.p1 - arrowLengthVec * direction + arrowWidthVec,
        edge.p1,
        ], 0)
    return arrowPath

def cursorMark(p, crossLength):
    radius = crossLength / 4
    vx     = pya.DVector(crossLength, 0)
    vy     = pya.DVector(0, crossLength)

    return [{
        "data"  : pya.DPolygon([p + misc.vectorRotate(pya.DVector(radius, 0), 360/32 * i) for i in range(33)]), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    },{
        "data"  : pya.DEdge(p + vy, p - vy), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    },{
        "data"  : pya.DEdge(p + vx, p - vx), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    }]
    
def detectRangeMark(p, detectRange):
    vxy          = pya.DVector(detectRange, detectRange)
    return [{
        "data"  : pya.DBox(p - vxy, p + vxy), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    }]

def centerMark(shape, crossLength):
    c  = shape.bbox().center()
    vx = pya.DVector(crossLength, 0)
    vy = pya.DVector(0, crossLength)
    return [{
        "data"  : pya.DEdge(c + vy, c - vy), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    },{
        "data"  : pya.DEdge(c + vx, c - vx), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    }]
    
def edgeArrowMark(edge, arrowLength, direction):
    return [{
        "data"  : edgeToArrowPath(edge, arrowLength, direction), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    }] 
    
def edgeCenterMark(edge, markLength):
    lengthVector = misc.vectorRotate((edge.d() / edge.length()) * markLength/2, 45)
    edgeCenter   = edge.p1 + edge.d()/2
    return [{
        "data"  : pya.DEdge(edgeCenter + lengthVector, edgeCenter - lengthVector), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    }] 

def vertexMark(p, crossLength):
    radius2  = crossLength / 4 * 2
    radius1  = crossLength / 4
    
    vx = pya.DVector(crossLength, 0)
    vy = pya.DVector(0, crossLength)
    
    return [{
        "data"  : pya.DPolygon([p + misc.vectorRotate(pya.DVector(radius2, 0), 360/32 * i) for i in range(33)]), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    },{
        "data"  : pya.DPolygon([p + misc.vectorRotate(pya.DVector(radius1, 0), 360/32 * i) for i in range(33)]), 
        "theme" : {"line_width" : 1, "line_style" : 0, "vertex_size" : 0}
    },{
        "data"  : pya.DEdge(p + vy, p - vy), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    },{
        "data"  : pya.DEdge(p + vx, p - vx), 
        "theme" : {"line_width" : 1, "line_style" : 1, "vertex_size" : 0}
    }]
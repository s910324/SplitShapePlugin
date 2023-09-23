import pya
import math

def dPixelLength(view, pixels):
    vp_trans    = view.viewport_trans()
    canvasRes   = max([view.viewport_height(), view.viewport_width()])
    dlength  = 1 / vp_trans.mag * pixels
    return dlength
    
def vectorRotate(v, angle):
    rad = angle * 0.0174533 
    return pya.DVector(v.x * math.cos(rad) - v.y * math.sin(rad), v.x * math.sin(rad) + v.y * math.cos(rad))
    
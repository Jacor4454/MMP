# this file contains functions that pertain to opening and processing the area masks
# basically its the main code's geopandas functions

import geopandas as gpd
from shapely import Polygon, MultiPolygon, make_valid
from shapely.ops import unary_union
import subprocess
from PIL import Image
import numpy as np

from pythonLibs.varsLib import ProgramVars

# load the layer geometry
def getLayerGeom(name : str, vars : ProgramVars):

    # translate to higher LOD name if in higher LOD mask
    if vars.LOD != 0:
        if name == "water":
            name = "sea"
        elif name == "urbanarea":
            name = "urbanarea_nat"

    # open file
    # the bbox variable means the model only returns data that exists in that area, 
    # but does not reduce the geometries to that area, so also need to clip the dataframe
    # using bbox does save space (as no irrelivent data is cached) 
    # and processing time (saw a 4x improvement over not using bbox)
    land_data = gpd.read_file(
        f"assets/ZoomstackUnpacked/{name}.gpkg",
        layer=name,
        bbox=(vars.minx-1, vars.miny-1, vars.maxx+1, vars.maxy+1)
    )
    # trim the grometries to the relevent area
    land_data =  land_data.clip((vars.minx-1, vars.miny-1, vars.maxx+1, vars.maxy+1))

    # create list of multi polygons
    # unpack geometries from dataframe into list of polygons
    mp = []
    for value in land_data["geometry"]:
        if(not value.is_valid):
            value = make_valid(value, method="structure")

        # if polygon, add polygon
        if(type(value) == Polygon):
            mp.append(value)
        
        # if multipolygon, add each part of multipolygon
        elif(type(value) == MultiPolygon):
            for p in list(value.geoms):
                mp.append(p)

        # should not happen as each layer is pure polygon geometry, but just in case
        else:
            raise f"unsupported geometry of type {type(value)} found"

    # compile list of polygons to multipolygon
    mp = MultiPolygon(mp)
    # merge polygons
    mp = unary_union(mp)
    # if union returns 1 object, turn back into multipolygon
    if(type(mp) == Polygon):
        mp = MultiPolygon([mp])
    # if it is still a polygon, then it is an empty geometry
    
    return mp

# compress and filters features by buffering geometries
def compress(mp : MultiPolygon, cr : int, vars : ProgramVars):
    # simplify here or the polygons get too complex and cause issues down the line
    mp = mp.buffer(-cr).simplify(vars.maxppmm * 50 * 0.1)
    mp = mp.buffer(cr)
    if(type(mp) == Polygon):
        mp = MultiPolygon([mp])
    # if it is still a polygon, then it is an empty geometry

    return mp

# convert from shapely polygons to string
def parseGeoms(mp : MultiPolygon, vars : ProgramVars):
    # if the input shape is a polygon, then one of the above functions triggered an empty geopmetry set, 
    # so the polygon is empty and we return empty
    if(type(mp) == Polygon):
        return "[]"
    
    # helper functions
    def prep(coord):
        return f"[{(coord[0]-vars.minx+1)},{(coord[1]-vars.miny+1)}]"
    def prep2(s):
        return f"[{','.join(map(str, s))}]"

    # convert each geometry to a list of points and paths
    # openscad needs the geoms in form on [points[],[exterior, interior...]]
    ops = []
    for p in list(mp.geoms):
        tp = list(p.exterior.coords)
        points = tp
        paths = [list(range(0, len(tp)))]

        # add interior points to points list, append paths to paths as seperate list
        for interior in p.interiors:
            tp = interior.coords
            points += tp
            paths.append(range(paths[-1][-1]+1, paths[-1][-1]+len(tp)+1))

        # convert points and paths to string
        ops.append(f"[[{','.join(map(prep, points))}],[{','.join(map(prep2, paths))}]]")

    # convert list of strings to a string
    return f"[{','.join(ops)}]"


# the images OpenSCAD renders have solid colour backdrop with no anti aliasing
# this function converts the solid colour [255,255,229] (the default background colour) to trasparent
def removeImgBackground(fName : str):
    # open image
    img = Image.open(fName)
    img = img.convert("RGBA")
    
    # convert img to array
    img_arr = np.array(img)

    # create templates for translation from/too
    bg_colour = np.array([255,255,229], np.uint8)
    transparent = np.array([0,0,0,0], np.uint8)
    
    # lambda function to convert bg_colour to transparent
    img_arr = np.apply_along_axis(lambda a: transparent if (a[:3] == bg_colour).all() else a, 2, img_arr)

    # convert array back to img and save
    img = Image.fromarray(img_arr)
    img.save(fName)
    
# render the output model from OpenSCAD into images for metadata/thumbnail
def renderImgs(genAll : bool, scadComm : str):
    subprocess.run([scadComm, "-o", "assets/sampled/plate_1.png", "--viewall", "--imgsize=512,512", "--backend=manifold", "OpenSCAD/display.scad"])
    removeImgBackground("assets/sampled/plate_1.png")
    if(genAll):
        subprocess.run([scadComm, "-o", "assets/sampled/plate_1_small.png", "--viewall", "--imgsize=128,128", "--backend=manifold", "OpenSCAD/display.scad"])
        subprocess.run([scadComm, "-o", "assets/sampled/top_1.png", "--camera=0,0,0,0,0,0,0", "--imgsize=512,512", "--viewall", "--backend=manifold", "OpenSCAD/display.scad"])
        removeImgBackground("assets/sampled/plate_1_small.png")
        removeImgBackground("assets/sampled/top_1.png")


# render the model and save to 3MF file
def render(shore : str, water : str, woods : str, greenspaces : str, urbanAreas : str, parks : str, vars : ProgramVars, arr_shape : tuple[int, int]):
    # save geoms and parameters to scad file
    with open("OpenSCAD/generatedData/polys.scad", "w+") as f:
        f.write(f"shorePolys={shore};\n" +
                f"waterPolys={water};\n" +
                f"woodsPolys={woods};\n" + 
                f"greenPolys={greenspaces};\n" + 
                f"urbanPolys={urbanAreas};\n" + 
                f"parksPolys={parks};\n" + 
                f"scaleRatio=[{50*vars.LODr()}, {50*vars.LODr()}, {vars.LODr()}];\n" + 
                f"useLine={str(vars.useGPX).lower()};\n" + 
                f"outputScaleRatio=[{0.02*vars.outputSize[0]/arr_shape[1]/vars.LODr()}, {0.02*vars.outputSize[1]/arr_shape[0]/vars.LODr()}, {0.02/vars.maxppmm/vars.LODr()}];\n" + 
                f"outputTranslate=[-{vars.outputSize[0]/2}, -{vars.outputSize[1]/2}, 0];\n" + 
                f"baseData=[{vars.new_dxr+vars.maxppmm*100}, {vars.new_dyr+vars.maxppmm*100}, {134+vars.maxppmm*50}];\n" + 
                f"baseTrans=[{-vars.maxppmm*50},{-vars.maxppmm*50},{-vars.maxppmm*50}];\n")

    # run subprocess
    subprocess.run([vars.openscadComm, "-o", "assets/sampled/WIP.3mf", "-O", "export-3mf/material-type=color", "--enable", "lazy-union", "--backend=manifold", "OpenSCAD/landMC.scad"])

    # run subprocess
    renderImgs(vars.addAllMetadata, vars.openscadComm)


# render in monochrome as 1 object
def mono_render(vars : ProgramVars, arr_shape : tuple[int, int]):
    # save geoms and parameters to scad file
    with open("OpenSCAD/generatedData/polys.scad", "w+") as f:
        f.write(f"scaleRatio=[{50*vars.LODr()}, {50*vars.LODr()}, {vars.LODr()}];\n" + 
                f"useLine={str(vars.useGPX).lower()};\n" + 
                f"outputScaleRatio=[{0.02*vars.outputSize[0]/arr_shape[1]/vars.LODr()}, {0.02*vars.outputSize[1]/arr_shape[0]/vars.LODr()}, {0.02/vars.maxppmm/vars.LODr()}];\n" + 
                f"outputTranslate=[-{vars.outputSize[0]/2}, -{vars.outputSize[1]/2}, 0];\n" + 
                f"baseData=[{vars.new_dxr+vars.maxppmm*100}, {vars.new_dyr+vars.maxppmm*100}, {134+vars.maxppmm*50}];\n" + 
                f"baseTrans=[{-vars.maxppmm*50},{-vars.maxppmm*50},{-vars.maxppmm*50}];\n")

    # run subprocess
    subprocess.run([vars.openscadComm, "-o", vars.outputFile if vars.isSTL else "assets/sampled/WIP.3mf", "-O", "export-3mf/material-type=color", "--backend=manifold", "OpenSCAD/landMono.scad"])

    # if saving model as stl, skip metadata generation
    if vars.isSTL:
        return
    
    # run subprocess
    renderImgs(vars.addAllMetadata, vars.openscadComm)
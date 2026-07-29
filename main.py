from shapely import get_coordinates, LineString
from pythonLibs.datLib import datFile
import numpy as np
import subprocess
import argparse, time
from pathlib import Path

from pythonLibs.gpsLib import getGpsLine, convertAndRange
from pythonLibs.geomLib import render, mono_render
from pythonLibs.varsLib import ProgramVars
from pythonLibs.mfLib import ColourMask, repackage


# funciton that calculates the boundaries the model will have
def calculateDataBounds(ranges, vars : ProgramVars):
    ranges = (ranges[0], ranges[2], ranges[1], ranges[3])

    # pad maxs and mins
    dxr = (ranges[1] - ranges[0])*(1 + (vars.modelPaddingPercent/100))
    dyr = (ranges[3] - ranges[2])*(1 + (vars.modelPaddingPercent/100))
    cx = (ranges[1] + ranges[0])/2
    cy = (ranges[3] + ranges[2])/2

    # get pixle density
    ppmmx = dxr / vars.outputSize[0] / 50
    ppmmy = dyr / vars.outputSize[1] / 50
    vars.maxppmm = max(ppmmx, ppmmy)

    # make ppmm equal by padding model
    vars.new_dxr = vars.maxppmm * vars.outputSize[0] * 50
    vars.new_dyr = vars.maxppmm * vars.outputSize[1] * 50

    # get new ranges
    vars.minx = cx - 0.5*(vars.new_dxr)
    vars.maxx = cx + 0.5*(vars.new_dxr)
    vars.miny = cy - 0.5*(vars.new_dyr)
    vars.maxy = cy + 0.5*(vars.new_dyr)

    # LOD calculations
    vars.LOD = 0
    if(vars.maxppmm >= 25):
        vars.LOD = 1
    if(vars.maxppmm >= 125):
        vars.LOD = 2

    # Warn user that using these layers at this LOD is not going to work well
    if vars.LOD > 0 and ("woods" in vars.layers or "shore" in vars.layers or "greenspaces" in vars.layers):
        print("unsupported detail render for input of this size, please remove woods/shore/greenspaces from layers or use presets tri-np, tri-ua, duo, mono, or true")


# helper function to render line
# seperated into this function to make main function more readable
def renderLine(line : LineString, vars : ProgramVars):
    # offset top line by 0.02mm, 0.5mm, or 1mm for LOD 0, 1, and 2 respectively
    top_offset = vars.maxppmm
    if(vars.LOD == 1):
        top_offset = vars.maxppmm*25
    elif(vars.LOD == 2):
        top_offset = vars.maxppmm*50

    # function to take a list of coordinates and convert to a string
    def parsePath(line):
        # function to convert 1 point into a str of coords
        def prep(coord):
            return f"[{(coord[0]-vars.minx+1)},{(coord[1]-vars.miny+1)},{coord[2] + top_offset}]"
        # for each coord, apply prep, then separate with commas between them
        return f"[{','.join(map(prep, line))}]"
    
    # simplify the linestring to 1/50th a mm resolution and repack as array of coordinates
    line = get_coordinates(line.simplify(tolerance=vars.maxppmm), include_z=True)

    # write array of coords to the linedata file
    # also line width (is actually line radius)
    with open("OpenSCAD/generatedData/lineData.scad", "w+") as f:
        f.write(f"points={parsePath(line)};\nwidth={vars.maxppmm*50*(vars.lineWidth/2)};\n")

    # call openscad
    subprocess.run([vars.openscadComm, "-o", "OpenSCAD/generatedData/line.stl", "--backend=manifold", "OpenSCAD/line.scad"])



def main():

    parser = argparse.ArgumentParser(description="convert GPX tracking data from within Great Britain, so a 3D model of that journey")
    inputGroup = parser.add_mutually_exclusive_group(required=True)
    inputGroup.add_argument(
        "--use-gpx", 
        action="store",
        default=None,
        help="Input GPX file"
    )
    inputGroup.add_argument(
        "--use-coords",
        action="store",
        nargs=4,
        default=None,
        help="sets the bound of the area to map",
    )
    parser.add_argument("output_file", help="Output 3MF/stl file (based off file extension provided, if not .stl then it is treated as 3mf file)")
    layerGroup = parser.add_mutually_exclusive_group(required=True)
    layerGroup.add_argument(
        "--layer-preset",
        action="store",
        default=None,
        choices=["true", "mono", "duo", "tri", "tri-np", "tri-ua", "all"],
        help="default/recommended layer presets",
    )
    layerGroup.add_argument(
        "--layers",
        action="extend",
        nargs="+",
        default=[],
        choices=["shore", "water", "woods", "greenspaces", "urbanarea", "parks"],
        help="layers to render, as a stack (so last object will be on top of the second to last, etc.)",
    )
    parser.add_argument(
        "--OpenSCAD",
        action="store",
        default="openscad-nightly",
        help="the openscad CLI name (depends on OpenSCAD and OS version, check your install)",
    )
    parser.add_argument(
        "--outputdims",
        action="store",
        nargs=2,
        default=["100", "100"],
        help="output dimension in mm in form 'x' 'y'.",
    )
    parser.add_argument(
        "--lineWidth",
        action="store",
        default="2",
        help="the width of the line of the model in mm",
    )
    parser.add_argument(
        "--featureFilter",
        action="store",
        default="0.2",
        help="the filter size of all model features (masks) in mm, i.e. min feature size in resulting model. Default 0.2mm",
    )
    parser.add_argument(
        "--featurePadding",
        action="store",
        default="0.1",
        help="the padding size of all model features (masks) in mm. Default 0.1mm",
    )
    parser.add_argument(
        "--modelPaddingPercent",
        action="store",
        default="20",
        help="percentage of the model that is padded, adding an extra X percent area to the bounding box",
    )
    parser.add_argument(
        "--addAllMetadata",
        action="store_true",
        help="generate extra internal image metadata, for some models adding this can add an extra minute.",
    )
    parser.add_argument(
        "--time",
        action="store_true",
        help="time the code running (for benchmarking)",
    )
    args = parser.parse_args()
    vars : ProgramVars = ProgramVars()
    vars.addArgs(args)

    # make directories that may not exist
    Path("./assets/sampled").mkdir(parents=True, exist_ok=True)
    Path("./OpenSCAD/generatedData").mkdir(parents=True, exist_ok=True)


    if vars.useGPX:
        print("loading file")
        route = getGpsLine(vars.inputFile)
        ranges = route.bounds
        calculateDataBounds(ranges, vars)
        print("loading file done")

        print("rendering line")
        renderLine(route, vars)
        print("rendering line done")
    else:
        ranges = convertAndRange(*vars.bounds)
        calculateDataBounds(ranges, vars)
        




    print("clipping data")
    
    range_x = (int(vars.minx//50) // 400, (int(vars.maxx//50) + 399) // 400)
    range_y = (int(vars.miny//50) // 400, (int(vars.maxy//50) + 399) // 400)

    x_start = int(vars.minx//50//vars.LODr())
    x_end = int(vars.maxx//50//vars.LODr())
    y_start = int(vars.miny//50//vars.LODr())
    y_end = int(vars.maxy//50//vars.LODr())

    areaTopology = np.zeros(shape=(y_end-y_start, x_end-x_start), dtype=np.uint16) + 134

    for x in range(*range_x):
        for y in range(*range_y):
            try:
                t = datFile.fromFile(f"assets/height_data/{vars.LOD}/{x}-{y}.dat").arr
            except:
                continue

            # t is range x*400, y*400
            # how to calculate the area this covers of :
            x_r_min = max(x*400 // vars.LODr(), x_start)
            x_r_max = min((x*400 + 400) // vars.LODr(), x_end)
            y_r_min = max(y*400 // vars.LODr(), y_start)
            y_r_max = min((y*400 + 400) // vars.LODr(), y_end)

            # calculate output array coord bounds :
            op_y_bound_min = y_r_min - y_start
            op_y_bound_max = y_r_max - y_start
            op_x_bound_min = x_r_min - x_start
            op_x_bound_max = x_r_max - x_start

            # calculate sample array coord bounds :
            t_y_bound_min = y_r_min-y * 400 // vars.LODr()
            t_y_bound_max = y_r_max-y * 400 // vars.LODr()
            t_x_bound_min = x_r_min-x * 400 // vars.LODr()
            t_x_bound_max = x_r_max-x * 400 // vars.LODr()

            areaTopology[op_y_bound_min:op_y_bound_max, op_x_bound_min:op_x_bound_max] = t[t_y_bound_min:t_y_bound_max, t_x_bound_min:t_x_bound_max]

    areaTopology = datFile(areaTopology)
    areaTopology.write("assets/sampled/main.dat")

    print("clipping data done")




    print("running model rendered")
    
    detail_factor = vars.maxppmm * 50 * vars.featureFilter
    detail_padding = vars.maxppmm * 50 * vars.featurePadding

    # load the user defined layers
    cm = ColourMask(vars.layers, vars, detail_factor, detail_padding)
    layers = cm.get_layers()

    if(vars.layers == False):
        mono_render(vars, areaTopology.arr.shape)
    else:
        render(*layers, vars, areaTopology.arr.shape)

    print("running model rendered done")

    if vars.isSTL:
        return






    print("repackaging")
    
    repackage("assets/sampled/WIP.3mf", "assets/bambu-tags.3mf", vars.outputFile, b"assets/bambu-tags", cm.get_used_indexs(), vars.addAllMetadata)
    
    print("repackaging done")


    # run the end timing
    if(vars.time == None):
        return
    
    print(f"code took {time.time() - vars.time} seconds to run")




if __name__ == "__main__":
    main()
 
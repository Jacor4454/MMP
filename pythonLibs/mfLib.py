# This file covers functions and classes related to handling layer data and 3MF data

# Inspite of it also being used to generate the masks for the renderer functions, 
# the ColourMask class definition is here because it is used my the repackage funciton, 
# and I deemed it as more closely related to 3MF than the rendered, 
# but either way its esentially a translation object

# the 3MF code is a little obfiscated, I will try to make it as clear as possible with comments,
# but the library itself it very... oldschool C++ orientated (heap-y and pointer-y), 
# but I will try my best


from shapely import MultiPolygon, Polygon, box
import lib3mf, os
from lib3mf import get_wrapper

from pythonLibs.varsLib import ProgramVars
from pythonLibs.geomLib import getLayerGeom, compress, parseGeoms


# the colourmask class is used for opening and organising the feature masks for the rendered, 
# as well as keeping track of which features are actually used for the 3MF repackager
class ColourMask:

    # the layers are their respective array pointers
    # basically an enum translater
    layerLookup = {
        "shore" : 0,
        "water" : 1,
        "woods" : 2,
        "greenspaces" : 3,
        "urbanarea" : 4,
        "parks" : 5,
    }

    # take the user defined list of layers, record which ones are actually visable, 
    # and provide the layer geoms to rendered and which layers are visable to repacker
    def __init__(self, layers : list[str] | bool, vars : ProgramVars, detail_factor : float, padding : float):
        self.layers : list[str] | bool = layers
    
        # the geometries as strings for the renderer
        self.toRender = ["[]" for _ in range(0, 6)]

        # a mask to show what area is currently covered in a mask
        topMP : MultiPolygon = MultiPolygon()

        # if monochrome, just finish
        if self.layers == False:
            self.usedIndexs = [1, 0, 0, 0, 0, 0, 0, 0]
            return

        # load the layers, pad/process, store if not empty
        self.layers.reverse()
        for layer in self.layers:
            if layer not in self.layerLookup.keys():
                raise IOError(-1, f"invalid layer input {layer}")

            # load the mask
            tempMP : MultiPolygon = compress(getLayerGeom(layer, vars).buffer(padding), detail_factor, vars)

            # remove previous masks from this mask
            toParse = tempMP.difference(topMP)

            # fun fact, if you convert a list of an empty polygon to a multipolygon, 
            #   it will return a polygon.
            # but if the polygon has any data at all, 
            #   it will return a multipolygon
            # this statment/conversion will filter out if any data that is blank
            if(type(toParse) == Polygon):
                toParse = MultiPolygon([toParse])
            
            # add this mask to full model mask
            topMP = tempMP.union(topMP)

            # convert to string, add to array
            self.toRender[self.layerLookup[layer]] = parseGeoms(toParse, vars)
        
        # a bit magic values-y ik but eh
        # land, park, urban, greensp, forest, water, shore, line
        self.usedIndexs = [
            # if sum of all masks covers whole model,
            #   remove main body from unpacker mask
            not box(0, 0, vars.maxx-vars.minx, vars.maxy-vars.miny).covered_by(topMP), 
            # if layer has data, add to repacker
            self.toRender[5] != "[]",
            self.toRender[4] != "[]", 
            self.toRender[3] != "[]", 
            self.toRender[2] != "[]", 
            self.toRender[1] != "[]", 
            self.toRender[0] != "[]", 
            # if using line, then use line...
            vars.useGPX]
    
    # getter for layer data (rendered)
    def get_layers(self):
        return self.toRender

    # getter for which layers are used (repacker)
    def get_used_indexs(self):
        return self.usedIndexs


# this is the repacker function
# this takes the raw painted model from the renderer and repackages it for slicers
# this is the obfiscated bit
def repackage(input : str, template : str, output : str, metadataLoc : bytes, used_geoms : list[int], genAllMeta : bool):
    # get lib3mf wrapper (handles lib3mf functional stuff like creating blank objects and constants)
    wrapper = get_wrapper()

    # open OpenSCAD output
    mData : lib3mf.Model = wrapper.CreateModel()
    mDataReader : lib3mf.Reader = mData.QueryReader("3mf")
    mDataReader.ReadFromFile(input)

    # get all meshs from data file
    # taken from github - [https://github.com/3MFConsortium/lib3mf/issues/460]
    def iter_objects(model : lib3mf.Model):
        it = model.GetObjects()
        while it.MoveNext():
            yield it.GetCurrentObject()
    # end of section taken from github

    # converts all meshs from the output (as they are all top level objects)
    meshs : list[lib3mf.MeshObject] = list(filter(lambda a : a.IsMeshObject(), iter_objects(mData)))

    # open template 3MF
    mTemplate : lib3mf.Model = wrapper.CreateModel()
    mTemplateReader : lib3mf.Reader = mTemplate.QueryReader("3mf")
    mTemplateReader.ReadFromFile(template)

    # get top level obejct from template
    compObjItt : lib3mf.ComponentsObjectIterator = mTemplate.GetComponentsObjects()
    compObjItt.MoveNext()
    compObj : lib3mf.ComponentsObject = compObjItt.GetCurrentComponentsObject()

    # for each part of the top level object
    #   if that part is used (using ColourMask.get_used_indexs output)
    #       store data from SCAD output in that part
    # basically matching SCAD output to the template objects
    geom_i = 0
    for i in range(0, compObj.GetComponentCount()):
        comp : lib3mf.Component = compObj.GetComponent(i)

        # make app parts relative to eachother
        comp.SetTransform(wrapper.GetIdentityTransform()) 

        obj : lib3mf.MeshObject = comp.GetObjectResource() # returns lib3mf.Object

        if(used_geoms[i]):
            obj.SetGeometry(meshs[geom_i].GetVertices(), meshs[geom_i].GetTriangleIndices())
            geom_i += 1
        else:
            obj.SetGeometry([], [])

    # add standard metadata (like filaments and slicer settings)
    for file in os.listdir(metadataLoc):
        target_attachment : lib3mf.Attachment = mTemplate.AddAttachment("/Metadata/" + file.decode("utf-8"), "")
        target_attachment.ReadFromFile((metadataLoc.decode("utf-8")+"/"+file.decode("utf-8")))

    # attach thumbnail
    target_attachment = mTemplate.AddAttachment("/Metadata/plate_1.png", "")
    target_attachment.ReadFromFile("assets/sampled/plate_1.png")
    target_attachment = mTemplate.AddAttachment("/Metadata/plate_no_light_1.png", "")
    target_attachment.ReadFromFile("assets/sampled/plate_1.png")
    mTemplate.RemovePackageThumbnailAttachment()
    target_attachment : lib3mf.Attachment = mTemplate.CreatePackageThumbnailAttachment()
    target_attachment.ReadFromFile("assets/sampled/plate_1.png")
    # attach other photos if user selected
    if(genAllMeta):
        target_attachment = mTemplate.AddAttachment("/Metadata/plate_1_small.png", "")
        target_attachment.ReadFromFile("assets/sampled/plate_1_small.png")
        target_attachment = mTemplate.AddAttachment("/Metadata/top_1.png", "")
        target_attachment.ReadFromFile("assets/sampled/top_1.png")

    # save repackaged model to file
    mTemplateWriter : lib3mf.Writer = mTemplate.QueryWriter("3mf")
    mTemplateWriter.WriteToFile(output)

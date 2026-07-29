import time

# container for the format info for the project
class ProgramVars:
    def __init__(self):
        self.minx : float = 0
        self.maxx : float = 0
        self.miny : float = 0
        self.maxy : float = 0

        self.LOD : int = 0
        self.LOD_OPS : list[int] = [1, 4, 16]

        self.maxppmm : float = 0

        self.outputSize : tuple[int, int] = (0, 0)

        self.layers : list[str] | bool[False] = []

        self.outputFile : str = ""
        self.inputFile : str = ""
        self.bounds : tuple[float, float, float, float] = (0, 0, 0, 0)
        self.useGPX : bool = True

        self.time = None

    # parses and stores the CLI arguments
    def addArgs(self, args):
        self.outputSize = (int(args.outputdims[0]), int(args.outputdims[1]))
        self.outputFile = args.output_file
        self.openscadComm = args.OpenSCAD
        self.isSTL = self.outputFile[-4:] == ".stl"
        self.lineWidth = float(args.lineWidth)
        self.featureFilter = float(args.featureFilter)
        self.featurePadding = float(args.featurePadding)
        self.addAllMetadata = args.addAllMetadata
        self.modelPaddingPercent = float(args.modelPaddingPercent)

        if(args.time):
            self.time = time.time()
        
        if(args.use_gpx == None):
            self.useGPX = False
            self.bounds = list(map(float, args.use_coords))
        else:
            self.inputFile = args.use_gpx

        # check for valid inputs
        # is also handled by argparse, so this shouldn't trigger
        if(args.layer_preset != None and len(args.layers) != 0):
            raise IOError(-1, "cannot use both layer-preset and layers flags")

        if(self.isSTL):
            self.layers = False
            print("stl output: forcing layer type to no-colour")
        elif(args.layer_preset):
            presetLookup = {
                "mono" : [],
                "duo" : ["water"],
                "tri" : ["water", "shore"],
                "tri-np" : ["parks", "water"],
                "tri-ua" : ["urbanarea", "water"],
                "all" : ["water","shore","parks","woods","urbanarea","greenspaces"],
                "true" : False
            }

            self.layers = presetLookup[args.layer_preset]
        else:
            self.layers = args.layers

    # get level of detail ratio value
    def LODr(self):
        return self.LOD_OPS[self.LOD]

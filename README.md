# 3D Modelling Terrain and Path Data - Undergraduate Major Project

## Overview
This project is an attempt to convert GPS tracking data or GPS coordinates to a 3D model. This is a CLI tool that takes either a .GPX file as an argument or a bounding box of GPS coordinates (I recommend just selecting a point on google maps, that will show a lat/long coordinate you can input)

## Prerequs/how to install 
This project requires python version >= 3.10.12

There is a requirements.txt file in the repo, so use this to install packages/libraries using: `pip install -r requirments.txt`

This project uses OpenSCAD CLI tools. To install this, go to the OpenSCAD website: https://openscad.org/downloads.html

At this time, some features can only be accessed in the nightly build, so I recommend installing that one
Development & testing used version _2026.01.24.nightly_, but theoretically any nightly version after this point should work

Once installed you can check the CLI is working by running: `openscad-nightly -h` in your command prompt/terminal

If there is an issue with the CLI command (in testing I know windows can be a pain for this) do not worry!
simply add the flag `--OpenSCAD` to the application arguments, followed by the location of the openscad executable
for instace adding:
`--OpenSCAD "C:\Program Files\OpenSCAD (Nightly)\openscad.exe"`
to my commands got the program working in windows

## Disclaimers
There is currently a bug where the output 3mf model is floating above the build plate, please groud the object (in Bambu or Orca this can be done with the auto-orientate button)

You will also see the output from OpenSCAD CLI commands, sometimes starting with "WARNING:". You do not need to worry about warnings like this, particularly:
 - WARNING: GeometryEvaluator: Node didn't fit into cache - this just means the heap got full and is calling the garbage collector
 - WARNING: Object 'OpenSCAD Model [number]' with UUID '[UUID]' is not valid, import() at line 1 - this is a side effect of blank top level geometry in some temp files, and will be removed before the main output

If an "ERROR" message comes up, please report it as an issue with a copy of the full command line output

# Contents
## main.py
### Overview
This is the main application. To use, open the project directory in your CLI of choice, and run:

`python main.py --help`

to print the argument help

all default arguments are geared towards a 0.2mm printer, so for a 0.4mm printer for instance, I recommend doubleing the default `--featurePadding` and `--featureFilter` parameters

I recommend sticking to layer presets (`--layer-preset [preset]`) as they will let you know if your selection is incompatable with an input area (larger area models can take a while with some features selected)

If you do use layers, use them in order, so
`-layers [1] [2] [3]`
will put layer 3 over layer 2, and layer 2 over layer 1
I also recommend always putting shore after water as water always covers all shore geometry

### CLI arguments
Here is the help output for CLI arguments:
```
usage: main.py [-h] (--use-gpx USE_GPX | --use-coords USE_COORDS USE_COORDS USE_COORDS USE_COORDS)
               (--layer-preset {true,mono,duo,tri,tri-np,tri-ua,all} | --layers {shore,water,woods,greenspaces,urbanarea,parks} [{shore,water,woods,greenspaces,urbanarea,parks} ...])
               [--OpenSCAD OPENSCAD] [--outputdims OUTPUTDIMS OUTPUTDIMS] [--lineWidth LINEWIDTH] [--featureFilter FEATUREFILTER] [--featurePadding FEATUREPADDING]
               [--modelPaddingPercent MODELPADDINGPERCENT] [--addAllMetadata] [--time]
               output_file

convert GPX tracking data from within Great Britain, so a 3D model of that journey

positional arguments:
  output_file           Output 3MF/STL file (based off file extension provided, if not .stl then it is treated as 3mf file)

options:
  -h, --help            show this help message and exit
  --use-gpx USE_GPX     Input GPX file
  --use-coords USE_COORDS USE_COORDS USE_COORDS USE_COORDS
                        sets the bound of the area to map
  --layer-preset {true,mono,duo,tri,tri-np,tri-ua,all}
                        default/recommended layer presets
  --layers {shore,water,woods,greenspaces,urbanarea,parks} [{shore,water,woods,greenspaces,urbanarea,parks} ...]
                        layers to render, as a stack (so last object will be on top of the second to last, etc.)
  --OpenSCAD OPENSCAD   the openscad CLI name (depends on OpenSCAD and OS version, check your install)
  --outputdims OUTPUTDIMS OUTPUTDIMS
                        output dimension in mm in form 'x' 'y'.
  --lineWidth LINEWIDTH
                        the width of the line of the model in mm
  --featureFilter FEATUREFILTER
                        the filter size of all model features (masks) in mm, i.e. min feature size in resulting model. Default 0.2mm
  --featurePadding FEATUREPADDING
                        the padding size of all model features (masks) in mm. Default 0.1mm
  --modelPaddingPercent MODELPADDINGPERCENT
                        percentage of the model that is padded, adding an extra X percent area to the bounding box
  --addAllMetadata      generate extra internal image metadata, for some models adding this can add an extra minute.
  --time                time the code running (for benchmarking)
```


Basically put, there are 2 forms of input:
`python main.py --use-file [GPX file] [output file]`
and
`python main.py --use-coords [lat 1] [long 1] [lat 2] [long 2] [output file]`

### examples
here are some examples/command templates to try:

render Aberystwyth in full colour with an 80mm by 80mm model:
`python3 main.py --outputdims 80 80 --layer-preset all --use-coords 52.394298 -4.104307 52.426026 -4.040449 output.3mf`

render Aberystwyth with just land/water/beaches with an 100mm by 100mm model:
`python3 main.py --layer-preset tri --use-coords 52.394298 -4.104307 52.426026 -4.040449 output.3mf`

template to render GPX journey with land/water/urban-areas(towns and cities) with a 80mm by 100mm model:
`python3 main.py --outputdims 80 100 --layer-preset tri-ua --use-gpx [GPX file] output.3mf`

### layer presets and features
I do recommend just having a play, but breifly:
 - `true` will render the whole model with no colour (will still be green in 3MF format)
 - `mono` will render the whole model as land(green)
 - `duo` will render the model with land(green) and sea/water(blue)
 - `tri` will render the model with land(green), shore(yellow), and sea/water(blue)
 - `tri-np` will render the model with land(green), national parks(brown), and sea/water(blue)
 - `tri-ua` will render the model with land(green), urban areas(grey), and sea/water(blue)
 - `all` will render the model with land(green), shore(yellow), national parks(brown), urban areas(grey), woods(dark green), greenspaces(light green), and sea/water(blue). Basically all layers available

I would recommend sticking to mono, duo, tri-np and tri-ua for larger models, but there will be a warning in the command output if a sample area is too big for efficint processing of a feature, so just play around and keep an eye out for "unsupported detail render for input of this size" in the first few lines of output. If you don't see that you're good

## preprocessor.py
### Overview
this prepairs the dataset, you do not need to run this in order to use the application, this is for development purposes, nothing more

## assets directory
### Overview
This director contains all the geospacial data and 3MF templates, already preprocessed and ready to use

It is recommended not to mess with this unless you know what you are doing (ie spoken to me or read my project report)

## pythonLibs directory
### Overview
location of python helper functions/classes, roughly grouped by theme/function.


## OpenSCAD directory
### Overview
location of OpenSCAD scripts.

# Credits
Parts of this project's assets are derived from Ordinance surveys' Zoomstack dataset and Terrain50 dataset.
Thank you to OS for the work you do.

Part of this code (labled in mfLib.py) is taken from code I was sent via an issue on the lib3mf github page by a maintainer.
Thank you to those guys for their assistance.

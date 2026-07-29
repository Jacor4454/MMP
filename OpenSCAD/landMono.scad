include <generatedData/polys.scad>

module line(){
    translate([0,0,140])import("generatedData/line.stl");
}

module body(){
    union(){
        scale(scaleRatio) surface(file = "../assets/sampled/main.dat", center = false, convexity = 5);
        if(useLine) line();
    }
}


translate(outputTranslate) scale(outputScaleRatio) body();

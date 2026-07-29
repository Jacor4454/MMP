include <generatedData/polys.scad>

linear_extrude_const = 100000;

                
module water(){
    for(a = waterPolys){
        polygon(a[0], a[1]);
    }
}

module shore(){
    for(a = shorePolys){
        polygon(a[0], a[1]);
    }
}

module woods(){
    for(a = woodsPolys){
        polygon(a[0], a[1]);
    }
}

module green(){
    for(a = greenPolys){
        polygon(a[0], a[1]);
    }
}

module urban(){
    for(a = urbanPolys){
        polygon(a[0], a[1]);
    }
}

module parks(){
    for(a = parksPolys){
        polygon(a[0], a[1]);
    }
}

module line(){
    translate([0,0,0]) import("generatedData/line.stl");
}


module body(){
    difference(){
        scale(scaleRatio) surface(file = "../assets/sampled/main.dat", center = false, convexity = 5);
        if(useLine) line();
    }
}




translate(outputTranslate) scale(outputScaleRatio) color("green")
    difference(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const)union(){
            water();
            shore();
            woods();
            green();
            urban();
            parks();
        };
    };

translate(outputTranslate) scale(outputScaleRatio) color("Olive")
    intersection(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const) parks();
    };

translate(outputTranslate) scale(outputScaleRatio) color("Gray")
    intersection(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const) urban();
    };

translate(outputTranslate) scale(outputScaleRatio) color("LawnGreen")
    intersection(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const) green();
    };

translate(outputTranslate) scale(outputScaleRatio) color("DarkGreen")
    intersection(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const) woods();
    };

translate(outputTranslate) scale(outputScaleRatio) color("blue")
    intersection(){
        body();
        translate([0,0,-20])linear_extrude(linear_extrude_const) water();
    };

translate(outputTranslate) scale(outputScaleRatio) color("yellow")
    intersection(){
        translate([0,0,-20])linear_extrude(linear_extrude_const) shore();
        body();
    };


if(useLine) translate(outputTranslate) scale(outputScaleRatio) color("red") line();

// color("blue") scale(outputScaleRatio) translate(baseTrans) cube(baseData);


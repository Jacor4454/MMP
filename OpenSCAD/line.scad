include <generatedData/lineData.scad>

// creates a line between 2 points, always has a very large part under the surface
module vector(p1, p2){
    hull(){
        translate(p1)translate([0,0,-100000+140]) cylinder(200000+width, width, width, center=true);
        translate(p2)translate([0,0,-100000+140]) cylinder(200000+width, width, width, center=true);
    };
}

module polyline(points){
    union(){
        for(a = [0:len(points)-2]){
            vector(points[a], points[a+1]);
        };
    }
}

difference(){
    polyline(points);
    translate([0,0,-3000000])cube([3000000,3000000,3000000]);
}

from typing import List
import numpy as np
import os
import geopandas as gpd
import pandas as pd
from shapely import box, normalize, Polygon, MultiPolygon, unary_union, difference
from pythonLibs.datLib import datFile
from tqdm import tqdm
import argparse
from pathlib import Path




# convert the unpacked ascii data in "dir" into a greyscale 16 bit png

class ASCII:
    def __init__(self, fileDir : str):
        self.parse(fileDir)

    def parse(self, fileDir : str):
        with open(fileDir, "r") as f:
            
            self.headers = {"ncols":0, "nrows":0, "xllcorner":0, "yllcorner": 0, "cellsize": 0}
            
            for _ in range(0, 5):
                k, v = f.readline().rstrip().split()
                self.headers[k] = int(v)
            
            if(self.headers["nrows"] != 200 or self.headers["ncols"] != 200):
                raise "cols/rows not 200"
            if(self.headers["cellsize"] != 50):
                raise "size not 50"

            self.data = []
            self.ranges = [99999, -99999]
            for _ in range(0, self.headers["nrows"]):
                cache = list(map(float, f.readline().rstrip().split()))
                if(len(cache) != self.headers["ncols"]):
                    raise "cols do not match"
                self.ranges = [min(self.ranges[0], min(cache)), max(self.ranges[1], max(cache))]
                self.data.append(cache)
            
            self.data = np.asarray(self.data, dtype=np.float16)

def cast(v, a, b, na, nb):
    return na + ((v-a) / (b-a)) * (nb-na)

class MAP:
    def __init__(self, inps : List[ASCII]):
        self.ranges = (99999, -99999)
        self.coords = (99999, -99999, 99999, -99999)

        cellsize = inps[0].headers["cellsize"]

        for inp in inps:
            if(inp.headers["cellsize"] != cellsize):
                raise "weird cellsize"
            self.ranges = [min(self.ranges[0], inp.ranges[0]), max(self.ranges[1], inp.ranges[1])]
            self.coords = [min(self.coords[0], inp.headers["xllcorner"]//cellsize), max(self.coords[1], inp.headers["xllcorner"]//cellsize + inp.headers["ncols"]), min(self.coords[2], inp.headers["yllcorner"]//cellsize), max(self.coords[3], inp.headers["yllcorner"]//cellsize + inp.headers["nrows"])]

        self.img = np.zeros([(self.coords[3]-self.coords[2]), (self.coords[1]-self.coords[0])], dtype=np.float16)
        self.img[:] = cast(0, self.ranges[0], self.ranges[1], 1, self.ranges[1]-self.ranges[0]+1)

        print(self.img.shape)
        print(self.coords)
        print(self.ranges)

        for inp in inps:
            a = self.img.shape[0]-(inp.headers["nrows"] + (inp.headers["yllcorner"]//cellsize)-self.coords[2])
            b = self.img.shape[0]-((inp.headers["yllcorner"]//cellsize)-self.coords[2])
            c = inp.headers["xllcorner"]//cellsize-self.coords[0]
            d = inp.headers["ncols"]+inp.headers["xllcorner"]//cellsize-self.coords[0]
            self.img[a:b, c:d] = inp.data - self.ranges[0] + 1


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="convert GPX tracking data from within Great Britain, so a 3D model of that journey")
    parser.add_argument("zoomstack", help="zoomstack gpkg (you may need to unzip the download)")
    parser.add_argument("terrain50", help="terrain 50 dataset location (zipped)")
    args = parser.parse_args()

    Path("./assets/raw_ascii").mkdir(parents=True, exist_ok=True)
    from zipfile import ZipFile
    with ZipFile(args.terrain50) as zO:
        zO.extractall(path="assets/terr50_gagg_gb")

    from pythonLibs.gaggUnpack import unpack
    unpack()

    asciis = []
    dir = b"assets/raw_ascii"
    bar = tqdm(os.listdir(dir))
    bar.set_description("Loading ASCII Data")
    for file in bar:
        if file.endswith(b".asc"):
            asciis.append(ASCII(os.path.join(dir, file)))

    print("mapping")
    height_arr = MAP(asciis).img
    height_arr = np.flip(height_arr, axis=0)
    print("mapping done")

    print("saving .dat")
    masterLandMask = gpd.read_file(
            args.zoomstack,
            layer="land"
        )

    def sample(masterMask, dataRaw, x, y):
        rx = x*400
        ry = y*400

        mask = masterMask.clip((rx*50, ry*50, (rx+400)*50, (ry+400)*50))
        
        
        if(len(mask.index) == 0):
            return
        
        # pull indexed sample from the main map
        raw = dataRaw[ry:ry+400, rx:rx+400]
        # convert from 400x400 to 100x100 by averaging 4x4 sample
        s1 = raw.reshape(100, 4, 100, 4).transpose(0, 2, 1, 3).mean(axis=(2,3))
        # convert from 100x100 to 25x25 by averaging 4x4 sample
        s2 = s1.reshape(25, 4, 25, 4).transpose(0, 2, 1, 3).mean(axis=(2,3))

        # write raw to file in no. 0 LOD directory
        a = datFile(raw)
        a.write(f"assets/height_data/0/{x}-{y}.dat")
        # write middle LOD to file in no. 1 LOD directory
        b = datFile(s1)
        b.write(f"assets/height_data/1/{x}-{y}.dat")
        # write lowest LOD to file in no. 2 LOD directory
        c = datFile(s2)
        c.write(f"assets/height_data/2/{x}-{y}.dat")

    lable1 = "Saving Values (By Column)"
    lable2 = "    Saving Column            "

    topBar = tqdm(range(0, height_arr.shape[1]//400))
    topBar.set_description(lable1)
    for x in topBar:
        bottomBar = tqdm(range(0, height_arr.shape[0]//400), leave=False)
        bottomBar.set_description(lable2)
        for y in bottomBar:
            sample(masterLandMask, height_arr, x, y)

    print("saving .dat done")







    # condence/preprocess zoomstack
    print("preparing water layer")

    land_data = gpd.read_file(
            args.zoomstack,
            layer="land",
        )
    bounds = box(0-2000000,0-2000000,660000+2000000,1230000+2000000)

    mp = []
    for value in land_data["geometry"]:
        if(type(value) == Polygon):
            mp.append(value)
        elif(type(value) == MultiPolygon):
            for p in list(value.geoms):
                mp.append(p)
        else:
            print("eeeee", type(value))
    mp = MultiPolygon(mp)
    mp = unary_union(mp)
    mp = bounds.difference(mp)


    water_data = gpd.read_file(
            args.zoomstack,
            layer="surfacewater",
        )

    water_data = pd.concat([water_data, gpd.GeoDataFrame([{"type":"Large", "geometry":mp}], crs=water_data.crs)], ignore_index=True)
    water_data.to_file("assets/ZoomstackUnpacked/water.gpkg", layer="water", driver="GPKG")

    sea_data = gpd.GeoDataFrame([{"type":"Large", "geometry":mp.simplify(tolerance=1000).buffer(100).buffer(-100)}], crs=water_data.crs)
    sea_data.to_file("assets/ZoomstackUnpacked/sea.gpkg", layer="sea", driver="GPKG")

    print("preparing water layer done")







    print("preparing urban area layer")
    ua_data = gpd.read_file(
            args.zoomstack,
            layer="urban_areas",
        )

    ua_data = ua_data.rename(columns={'type':'region'})
    ua_data_reg = ua_data[ua_data.region == "Regional"]
    ua_data_nat = ua_data[ua_data.region == "National"]

    ua_data_reg.to_file("assets/ZoomstackUnpacked/urbanarea.gpkg", layer="urbanarea", driver="GPKG")
    ua_data_nat.to_file("assets/ZoomstackUnpacked/urbanarea_nat.gpkg", layer="urbanarea_nat", driver="GPKG")

    print("preparing urban area layer done")








    def prepairLayer(name : str, layerRef : str):
        print(f"preparing {name} layer")

        shore_data = gpd.read_file(
                args.zoomstack,
                layer=layerRef,
            )
        shore_data.to_file(f"assets/ZoomstackUnpacked/{name}.gpkg", layer=name, driver="GPKG")

        print(f"preparing {name} layer done")

    layers = [("shore", "foreshore"), ("woods", "woodland"), ("greenspaces", "greenspace"), ("parks", "national_parks")]

    for layer in layers:
        prepairLayer(*layer)

    print("saving masks done")
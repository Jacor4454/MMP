import geopandas as gpd
from shapely import Point, LineString, get_coordinates
import gpxpy

# convert the 2 coordinates from globle GPS to local/GB coords
def convertAndRange(y1, x1, y2, x2):
    frame = gpd.GeoDataFrame([Point(x1, y1), Point(x2, y2)], columns=["geometry"], crs="EPSG:4326")
    frame = frame.to_crs("EPSG:27700")
    toret1 = list(frame.itertuples())[0][1].xy
    toret2 = list(frame.itertuples())[1][1].xy

    return toret1[0][0], toret1[1][0], toret2[0][0], toret2[1][0]




# this function is modified code from the pip page for gpxpy
def getGpsLine(fname: str) -> LineString:
    gpx = None
    with open(fname, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    x = []
    y = []
    z = []
    
    # open all parts of the file and append to coords
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                x.append(point.longitude)
                y.append(point.latitude)
                z.append(point.elevation)

    # load to geodataframe and convert from globle GPS to local/GB coords
    line = gpd.GeoDataFrame([LineString(list(zip(x,y,z)))], columns=["geometry"], crs="EPSG:4326")
    line = line.to_crs(crs="EPSG:27700")

    return line['geometry'][0]


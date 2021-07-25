#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import argparse
import numpy as np
import pdal
import json
from osgeo import osr
from osgeo import ogr
from osgeo import gdal
import geopandas as gpd
from geopandas import GeoDataFrame
import fiona

parser = argparse.ArgumentParser(description="generate DEM")

## LiDAR input path
parser.add_argument('--InputPath','-I', type=str, required=True,                    help="Please indicate the file path that points to the location of the .las data")
parser.add_argument('--ContourPath', '-CP', type=str, required=True,                    help="Please indicate the file path to save the contour map")
#default="/C/contours.shp",
## SMRF Parameters
parser.add_argument('--smrfthreshold','-t', type=float, required=False, default= 0.5,                    help="Simple Morphological Filter elevation threshold parameter (meters). Default: 0.5")

parser.add_argument('--smrfwindow','-w', type=int, required=False, default= 18.0,                    help="Simple Morphological Filter window radius parameter(meters). Default: 18.0")

parser.add_argument('--smrfscalar','-s', type=float, required=False, default=1.25,                   help="Simple Morphological Filter elevation scalar parameter. Default: 1.25")

parser.add_argument('--smrfslope','-sl', type=float, required=False , default=0.15,                    help="Simple Morphological Filter slope parameter. Default: 0.15")

## DEM Output Parameters
parser.add_argument('--Resolution','-r', type=float, required=True,                    help="Length of raster cell")
parser.add_argument('--windowSize','-ws', type=int, required=True,                    help="Attempt to fill nodata areas with data inferred from valid cells")

## Contour Output Parameters
parser.add_argument('--Intervals','-In', type=int, required=False , default=10,                    help="This defines contour intervals")
                    
arguments = parser.parse_args()                    

## Point Cloud 2 DEM
lasfile = arguments.InputPath   
pipeline = [
        {
            "type": "readers.las",
            "filename": lasfile
            },
    {  #Apply a value of 0 to the Classification dimension for every point
      "type":"filters.assign",
      "assignment":"Classification[:]=0"
    },
     {   #Noise detection
      "type":"filters.elm",
       "cell":1,
      "threshold":0.25
    },
    { #Outlier detection
       "type":"filters.outlier",
       "multiplier":3.0, 
       "mean_k":32, 
       "method":"statistical" 
     },
    {  
        "type":"filters.smrf",
        "ignore":"Classification[7:7]",
        "scalar":arguments.smrfscalar,
        "slope":arguments.smrfslope,
        "window":arguments.smrfwindow,
        "threshold":arguments.smrfthreshold
    },
    { 
        "type":"filters.range",
        "limits":"Classification[2:2]"   
    },
    { 
        "type":"writers.gdal",
        "filename":"DEM.tif",
        "gdaldriver":"GTiff", 
        "window_size":arguments.windowSize,   
        "resolution":arguments.Resolution ,   
        "output_type":"idw"
    }
]
pipeline = pdal.Pipeline(json.dumps(pipeline))
pipeline.execute()

## DEM 2 Contour.shp
rasterDs = gdal.Open('DEM.tif')
proj = osr.SpatialReference(wkt=rasterDs.GetProjection())
contourDs = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(arguments.ContourPath)
contourShp = contourDs.CreateLayer('contour', proj)
fieldDef = ogr.FieldDefn("ID", ogr.OFTInteger)
contourShp.CreateField(fieldDef)
fieldDef = ogr.FieldDefn("elev", ogr.OFTReal)
contourShp.CreateField(fieldDef)
gdal.ContourGenerate(rasterDs.GetRasterBand(1), arguments.Intervals, 0, [], 1, -9999., contourShp, 0, 1)
contourDs.Destroy()
## Contour.shp 2 Contour.dxf
x = gpd.read_file(arguments.ContourPath)
x.geometry.to_file('Contour.dxf', driver="DXF")


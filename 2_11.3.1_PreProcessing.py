# ============PRE-PROCESS PREVIOUSLY DOWNLOADED SENTINEL-2 IMGS=================
# Natalia Verde, AUTh, February 2019

# 2nd script for 11.3.1 indicator
# part of the SDG indicator 11.3.1 workflow for VLab Workshop in Florence, February 2019

# This script unzips the previously downloaded Sentinel-2 images, creates a stack for the 20m-bands and exports
# as a geotiff. After that, the images are clipped to an Area Of Interest (AOI) and are mosaicked.
# INPUTS: 1. Shapefile with one closed polygon of the AOI in EPSG CRS same as the downloaded tiles

# ==============IMPORTS=============================================

import os
import pathlib
import glob
import zipfile
from datetime import *

import gdal
from gdal import osr, ogr

# =================SETTINGS=========================================

# define area of interest (aoi) shapefile (only name - must be in project directory)
# must be a shapefile with only one polygon
aoiPath = "aoi.shp"

# =============FUNCTIONS============================================


def unzip(zippath):
    # extract all zipped images in dataPath
    for filename in glob.glob(os.path.join(str(zippath),  '*.zip')):
        # extract S2 downloaded images
        zip_ref = zipfile.ZipFile(filename, 'r')
        zip_ref.extractall(str(zippath))
        zip_ref.close()
        print("---------------------------------------------")
        print("Unzipped product", str(os.path.splitext(os.path.basename(filename))[0]))


def stack20ms2tiff(datapath, exportpath):
    # read and stack all 20m bands of S2 images, convert to tiff
    for directory in os.listdir(str(cwd / datapath)):
        if '__MACOSX' in directory:
            continue
        productPath = str(cwd / datapath / directory)
        productName = os.path.splitext(directory)[0]
        if os.path.isdir(productPath):
            print("---------------------------------------------")
            print('processing file', str(os.path.splitext(os.path.basename(productPath))[0]))
            granulePath = os.path.join(str(productPath), "GRANULE")
            folderList = os.listdir(str(granulePath))
            path20m = os.path.join(str(granulePath), folderList[0], "IMG_DATA", "R20m")
            # get only real bands (B01, B02 etc)
            img20m_list = glob.glob(os.path.join(path20m, '*B*.jp2'))
            # stack and convert to tiff
            outvrt = os.path.join(cwd, exportpath, '/vsimem/stacked.vrt')  # /vsimem is special in-memory virtual "directory"
            outtif = os.path.join(cwd, exportpath, str(productName + '_stacked.tif'))
            outds = gdal.BuildVRT(outvrt, img20m_list, separate=True)  # 'separate" is for gdal to stack bands
            gdal.Translate(outtif, outds)

            # Close datasets
            outds = None

            print("file", str(os.path.splitext(os.path.basename(productPath))[0]),
                  "is now a multiband tiff in folder 'Mul_TIFFS'")


def clip_image(gdalvector, imgpath, outpath):

    imageName = str(os.path.splitext(os.path.basename(imgpath))[0])
    Raster = gdal.Open(str(imgpath))  #, gdal.GA_ReadOnly)
    # get projection
    proj = osr.SpatialReference(wkt=Raster.GetProjection())
    epsgCode = proj.GetAttrValue('AUTHORITY', 1)
    Projection = str("EPSG:" + epsgCode)
    # get pixel size
    gt = Raster.GetGeoTransform()
    PixelRes = round(gt[1])

    # get first feature from vector
    layer = gdalvector.GetLayer()
    feature = layer.GetFeature(0)
    geom = feature.GetGeometryRef()
    minX, maxX, minY, maxY = geom.GetEnvelope()  # Get bounding box of the shapefile feature

    # Create raster
    OutTileName = os.path.join(outpath, str(imageName + '_aoi.tif'))
    OutTile = gdal.Warp(OutTileName, Raster, format='GTiff', outputBounds=[minX, minY, maxX, maxY], xRes=PixelRes,
                        yRes=PixelRes, dstSRS=Projection, resampleAlg=gdal.GRA_NearestNeighbour)

    # Close datasets
    OutTile = None
    Raster = None

    print("---------------------------------------------")
    print("Clipped " + imageName)


def mosaic_images(folderpath):

    imgs_list = glob.glob(os.path.join(folderpath, "*.tif"))
    mosvrt = os.path.join(folderpath, '/vsimem/mosaic.vrt')  # /vsimem is special in-memory virtual "directory"
    outtif = os.path.join(folderpath, 'clipped-mos.tif')
    outds = gdal.BuildVRT(mosvrt, imgs_list)
    gdal.Translate(outtif, outds)

    # Close datasets
    outds = None

    print("---------------------------------------------")
    print("Made mosaic")


# =============MAIN PROGRAM=========================================

startedTime = datetime.now(timezone.utc)

# NOTE: If you are running a docker container through PyCharm, your path is in the PyCharm project directory.

# get current working directory
cwd = pathlib.Path.cwd()
downPath = os.path.join(str(cwd), "Downloads")

# extract all zipped images in Past folder
unzip(os.path.join(downPath, "Past"))
# extract all zipped images in Now folder
unzip(os.path.join(downPath, "Now"))

# create a folder for Stacked TIFF products
if not os.path.exists("Mul_TIFFS"):
    os.makedirs("Mul_TIFFS")
tiffPath = pathlib.Path("Mul_TIFFS")


# set the folder where your data exists
nowDatPath = pathlib.Path("Downloads/Now")

# set folder for stacked tiff export
if not os.path.exists(os.path.join(tiffPath, "Now")):
    os.makedirs(os.path.join(tiffPath, "Now"))
nowPath = os.path.join(tiffPath, "Now")


# set the folder where your data exists
pastDatPath = pathlib.Path("Downloads/Past")

# set folder for stacked tiff export
if not os.path.exists(os.path.join(tiffPath, "Past")):
    os.makedirs(os.path.join(tiffPath, "Past"))
pastPath = os.path.join(tiffPath, "Past")

stack20ms2tiff(pastDatPath, pastPath)


stack20ms2tiff(nowDatPath, nowPath)

endedTime = datetime.now(timezone.utc)

# clip to area of interest (aoi) and create mosaic-----------------------
# if folder contains more than one tile, mosaic them ---------------------

# Open aoi shapefile
VectorFormat = 'ESRI Shapefile'
VectorDriver = ogr.GetDriverByName(VectorFormat)
aoiVectorDataset = VectorDriver.Open(os.path.join(cwd, aoiPath), 0)  # 0=Read-only, 1=Read-Write
# Check to see if shapefile is found.
if aoiVectorDataset is None:
    print("---------------------------------------------")
    print('Could not open ' + str(aoiPath))
else:
    print("---------------------------------------------")
    print('Opened ' + str(aoiPath))
    layer = aoiVectorDataset.GetLayer()

# create a folder for mosaicked clipped TIFF products
if not os.path.exists("Clipped-Mos"):
    os.makedirs("Clipped-Mos")
tiffPath = pathlib.Path("Clipped-Mos")

# Now
nowPath = os.path.join(cwd, "Mul_TIFFS", "Now", "*.tif")
# set folder for clipped tiff mosaic export
if not os.path.exists(os.path.join(tiffPath, "Now")):
    os.makedirs(os.path.join(tiffPath, "Now"))
nowPathClip = os.path.join(tiffPath, "Now")
for filename in glob.glob(nowPath):
    if '__MACOSX' in filename:
        continue
    clip_image(aoiVectorDataset, filename, os.path.join(cwd, nowPathClip))  # clip
mosaic_images(os.path.join(cwd, nowPathClip))  # mosaic


# Past
pastPath = os.path.join(cwd, "Mul_TIFFS", "Past", "*.tif")
# set folder for clipped tiff mosaic export
if not os.path.exists(os.path.join(tiffPath, "Past")):
    os.makedirs(os.path.join(tiffPath, "Past"))
pastPathClip = os.path.join(tiffPath, "Past")
for filename in glob.glob(pastPath):
    if '__MACOSX' in filename:
        continue
    clip_image(aoiVectorDataset, filename, os.path.join(cwd, pastPathClip))  # clip
mosaic_images(os.path.join(cwd, pastPathClip))  # mosaic



print("---------------------------------------------")
print("Pre-processing completed in " + str(endedTime - startedTime))
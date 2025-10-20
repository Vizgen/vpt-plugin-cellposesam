import numpy as np
from pathlib import Path
from tqdm import trange
import matplotlib.pyplot as plt
from natsort import natsorted
import cv2
import rasterio
import rasterio.features
import geopandas as gp
from affine import Affine
from shapely import wkt
import pandas as pd
import time
from .vis_utils import draw_polygons, raster_to_polygons, color_mask
from . import models

def load_image_vzg():
    data_folder = "/home/ruben/data/vizgen_sample_dataset/202305010900_U2OS_small_set_VMSC00000/region_0/images/"
    img = np.zeros((3960, 3953, 3), dtype=np.uint8)
    im_files = {}

    im_files[0] = f"{data_folder}/mosaic_DAPI_z3.tif"
    im_files[1] = f"{data_folder}/mosaic_Cellbound2_z3.tif"
    im_files[2] = f"{data_folder}/mosaic_Cellbound3_z3.tif"

    for i in range(3):      
        im = cv2.imread(im_files[i], cv2.IMREAD_UNCHANGED)

        # normalize image
        if "DAPI" in im_files[i]:
            im = im / np.max(im)*100
        else:
            im = im / np.max(im)*255
        im = im.astype(np.uint8)
        img[:,:,i] = im
    return img

def color_mask(mask):
    labels = mask.astype(np.int32)
    num_labels = int(labels.max()) + 1

    # Assign a random color to each cell label, keep background (0) black
    rng = np.random.default_rng(42)
    colors = rng.integers(0, 256, size=(num_labels, 3), dtype=np.uint8)
    colors[0] = (0, 0, 0)
    mask = colors[labels]
    return mask
    
# io.logger_setup() # run this to get printing of progress

model = models.CellposeModel(gpu=True)

#img = load_image_vzg()

#file = "test-data/img_cellbounds2.png"
file = "test-data/DAPI_tile.png"

img = cv2.imread(file, cv2.IMREAD_UNCHANGED)

print(img.shape, img.dtype)

flow_threshold = 0.4
cellprob_threshold = 0.0
tile_norm_blocksize = 0

t = time.time()
masks, flows, styles = model.eval(img, batch_size=32, flow_threshold=flow_threshold, cellprob_threshold=cellprob_threshold,
                                  normalize={"tile_norm_blocksize": tile_norm_blocksize})
print("exec time: ", time.time() - t)

# Convert input image to uint8 for display
print(f"Cells detected: {masks.max()}")

# Show masks 
masks_visual = color_mask(masks)
if img.ndim == 2:
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

cv2.namedWindow('results', cv2.WINDOW_NORMAL)
cv2.resizeWindow('results', 1024, 512)
cv2.imshow("results", cv2.hconcat([img, 
                                   masks_visual, 
                                   flows[0].astype(np.uint8)]))

cv2.waitKey(0)


# Show outlines 
cell_polygons = raster_to_polygons(masks, masks != 0)
print(f"Cells polygons: {len(cell_polygons)}")
if img.ndim == 2:
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
im_rgb_cellpose_sam = draw_polygons(img, cell_polygons)

cv2.namedWindow('polygons', cv2.WINDOW_NORMAL)
cv2.resizeWindow('polygons', 1024, 512)
cv2.imshow("polygons", cv2.hconcat([img, im_rgb_cellpose_sam]))
cv2.waitKey(0)
cv2.destroyAllWindows()

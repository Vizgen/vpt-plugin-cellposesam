import numpy as np
import cv2
import geopandas as gp
from affine import Affine
import rasterio
import rasterio.features


def color_mask(mask):
    labels = mask.astype(np.int32)
    num_labels = int(labels.max()) + 1

    # Assign a random color to each cell label, keep background (0) black
    rng = np.random.default_rng(42)
    colors = rng.integers(0, 256, size=(num_labels, 3), dtype=np.uint8)
    colors[0] = (0, 0, 0)
    mask = colors[labels]
    return mask


def draw_polygons(im_rgb, gdf, thickness=1):
    # Draw geometries on the image
    im_rgb_ = im_rgb.copy()
    for geom in gdf["geometry"]:
        if geom.geom_type == "Polygon":
            # Convert polygon to a format suitable for cv2.polylines
            coords = np.array(geom.exterior.coords, dtype=np.int32)
            cv2.polylines(im_rgb_, [coords], isClosed=True, color=(0, 255, 100), thickness=thickness)
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:  # Corrected to iterate over geom.geoms
                coords = np.array(poly.exterior.coords, dtype=np.int32)
                cv2.polylines(im_rgb_, [coords], isClosed=True, color=(0, 255, 0), thickness=thickness)
    return im_rgb_


def raster_to_polygons(im_labels, mask, pixel_area_mm2=None, pixel_size_scaling=1.0):
    # Create polygons from image
    polygons = []
    transform = Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    gpd_polygons = gp.GeoDataFrame()
    if im_labels.shape[0] > 0 and im_labels.shape[1] > 0:
        for i, (s, v) in enumerate(rasterio.features.shapes(im_labels, mask=mask, transform=transform)):
            polygons.append({"properties": {"raster_val": v}, "geometry": s})
        if len(list(polygons)) > 0:
            gpd_polygons = gp.GeoDataFrame.from_features(list(polygons))
            if pixel_area_mm2 is not None:
                if pixel_size_scaling > 1.2 or pixel_size_scaling < 0.8:
                    factor = pixel_area_mm2 * 1e6 * pixel_size_scaling * pixel_size_scaling
                else:
                    factor = pixel_area_mm2 * 1e6
                gpd_polygons["area"] = gpd_polygons.geometry.area * factor
    return gpd_polygons

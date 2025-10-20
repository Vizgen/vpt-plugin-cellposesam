from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from vpt_core.io.image import ImageSet
from vpt_plugin_cellpose import CellposeSegProperties, CellposeSegParameters
from vpt_plugin_cellpose.predict import run


@dataclass(frozen=True)
class Circle:
    x: int
    y: int
    radius: int


def generate_images(image_size: int, cells: List[Circle]) -> Tuple[ImageSet, str, str]:
    dapi = np.ones((image_size, image_size), dtype=np.uint16)
    polyt = np.ones((image_size, image_size), dtype=np.uint16)
    for cell in cells:
        cv2.circle(dapi, (cell.x, cell.y), int(cell.radius * 0.8), (255, 255, 255), -1)
        cv2.circle(polyt, (cell.x, cell.y), int(cell.radius * 1.5), (255, 255, 255), -1)

    nuclear_channel, fill_channel = "DAPI", "PolyT"
    images = ImageSet()
    images[nuclear_channel] = {i: dapi for i in range(3)}
    images[fill_channel] = {i: polyt for i in range(3)}
    return images, nuclear_channel, fill_channel


def test_run_prediction() -> None:
    cells = [Circle(20, 15, 10), Circle(30, 100, 10), Circle(100, 20, 15), Circle(210, 100, 15)]
    images, nuc, fill = generate_images(256, cells)
    properties = CellposeSegProperties("cyto2", "2D", "latest", None)
    parameters = CellposeSegParameters(nuc, fill, 30, 0.95, -5.5, 256)
    mask = run(images, properties, parameters)
    for i in images.z_levels():
        labels = np.unique(mask[i, :, :])
        assert len(labels) == len(cells) + 1
        intersection = np.logical_and(mask[i] > 0, images[fill][i] > 1)
        union = np.logical_or(mask[i] > 0, images[fill][i] > 1)
        assert np.sum(intersection) / (np.sum(union) + 1e-15) > 0.7

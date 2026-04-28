import warnings

import numpy as np
from .cellposesam import models

from vpt_core.io.image import ImageSet
from vpt_plugin_cellposesam import CellposeSegProperties, CellposeSegParameters


def run(images: ImageSet, properties: CellposeSegProperties, parameters: CellposeSegParameters) -> np.ndarray:
    warnings.filterwarnings("ignore", message=".*the `scipy.ndimage.filters` namespace is deprecated.*")

    is_valid_channels = parameters.nuclear_channel and parameters.entity_fill_channel
    image = (
        images.as_stack([parameters.nuclear_channel, parameters.entity_fill_channel])
        if is_valid_channels
        else images.as_stack()
    )

    empty_z_levels = set()
    for z_i, z_plane in enumerate(image):
        for channel_i in range(z_plane.shape[-1]):
            if z_plane[..., channel_i].std() < 0.1:
                empty_z_levels.add(z_i)
    if len(empty_z_levels) == image.shape[0]:
        return np.zeros((image.shape[0],) + image.shape[1:-1])

    if properties.custom_weights:
        model = models.CellposeModel(gpu=True, pretrained_model=properties.custom_weights)
    else:
        model = models.CellposeModel(gpu=True)
    to_segment_z = list(set(range(image.shape[0])).difference(empty_z_levels))

    input_image = np.squeeze(image[to_segment_z, ...])

    z_axis = 0 if properties.model_dimensions == "3D" else None
    channel_axis = len(image.shape) - 1 if properties.model_dimensions == "3D" else None

    mask = model.eval(
        input_image,
        z_axis=z_axis,
        channel_axis=channel_axis,
        diameter=parameters.diameter,
        flow_threshold=parameters.flow_threshold,
        cellprob_threshold=parameters.cellprob_threshold,
        resample=False,
        min_size=parameters.minimum_mask_size,
        do_3D=(properties.model_dimensions == "3D"),
    )[0]

    mask = mask.reshape((len(to_segment_z),) + image.shape[1:-1])
    for i in empty_z_levels:
        mask = np.insert(mask, i, np.zeros(image.shape[1:-1]), axis=0)
    return mask

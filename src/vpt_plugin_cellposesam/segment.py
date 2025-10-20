from typing import Dict, Optional, List, Iterable, Union

import pandas as pd


from vpt_core.io.image import ImageSet
from vpt_core.segmentation.polygon_utils import generate_polygons_from_mask
from vpt_core.segmentation.seg_result import SegmentationResult
from vpt_core.segmentation.segmentation_base import SegmentationBase
from vpt_plugin_cellposesam import predict, CellposeSegProperties, CellposeSegParameters


class SegmentationMethod(SegmentationBase):
    @staticmethod
    def run_segmentation(
        segmentation_properties: Dict,
        segmentation_parameters: Dict,
        polygon_parameters: Dict,
        result: List[str],
        images: Optional[ImageSet] = None,
        transcripts: Optional[pd.DataFrame] = None,
    ) -> Union[SegmentationResult, Iterable[SegmentationResult]]:
        properties = CellposeSegProperties(**segmentation_properties)
        parameters = CellposeSegParameters(**segmentation_parameters)

        masks = predict.run(images, properties, parameters)
        return generate_polygons_from_mask(masks, polygon_parameters)

    @staticmethod
    def validate_task(task: Dict) -> Dict:
        nuclear_channel = task["segmentation_parameters"].get("nuclear_channel", None)
        fill_channel = task["segmentation_parameters"].get("entity_fill_channel", None)

        channels = [input_data["image_channel"] for input_data in task["task_input_data"]]

        if nuclear_channel and nuclear_channel not in channels:
            raise ValueError(f"{nuclear_channel} is not in input channels")

        if fill_channel and fill_channel not in channels:
            raise ValueError(f"{fill_channel} is not in input channels")

        return task

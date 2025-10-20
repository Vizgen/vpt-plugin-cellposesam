import json
from typing import Dict

from vpt_core.segmentation.seg_result import SegmentationResult

from tests.vpt_plugin_cellpose import TEST_DATA_ROOT
from tests.vpt_plugin_cellpose.test_predict import Circle, generate_images
from vpt_plugin_cellpose.segment import SegmentationMethod


def get_test_task(file_name: str) -> Dict:
    with open(TEST_DATA_ROOT / file_name, "r") as f:
        data = json.load(f)
        task = data["segmentation_tasks"][0]
    return task


def test_segment_validation() -> None:
    method = SegmentationMethod()
    task = get_test_task("cellpose.json")
    method.validate_task(task)

    wrong_task = get_test_task("wrong_task.json")
    try:
        method.validate_task(wrong_task)
        assert False
    except ValueError:
        pass


def test_segment_run() -> None:
    method = SegmentationMethod()
    task = get_test_task("cellpose.json")
    cells = [Circle(20, 15, 10), Circle(30, 100, 10), Circle(100, 20, 15), Circle(210, 100, 15)]
    seg_res = method.run_segmentation(
        segmentation_properties=task["segmentation_properties"],
        segmentation_parameters=task["segmentation_parameters"],
        polygon_parameters=task["polygon_parameters"],
        result=["cell"],
        images=generate_images(256, cells)[0],
    )
    for _, z_seg in seg_res.df.groupby(SegmentationResult.z_index_field):
        assert len(z_seg) == len(cells)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Coverage Status](https://coveralls.io/repos/github/Vizgen/vpt-plugin-cellposesam-internal/badge.svg)](https://coveralls.io/github/Vizgen/vpt-plugin-cellposesam-internal)

# CellposeSAM Plugin for VPT

This Vizgen Post-processing Tool (VPT) plugin enables users to run
[CellposeSAM](https://github.com/MouseLand/cellpose) (Cellpose v4) cell segmentation on MERSCOPE
experiments. VPT is a command line tool that emphasizes scalable, reproducible
analysis, and can be run on a workstation, a cluster, or be deployed in a cloud
computing environment. **Linux is recommended for production use.**


## Key Features

- Cell segmentation using CellposeSAM (Cellpose 4.0 + Segment Anything Model)
- Explicit nuclear and cell-body channel selection via `nuclear_channel`
  and `entity_fill_channel` parameters
- Tunable detection parameters: cell `diameter`, `flow_threshold`,
  `cellprob_threshold`, and `minimum_mask_size`
- Bring your own weights via the `custom_weights` path
- GPU-accelerated (CPU mode is available for testing only)
- Full VPT integration: tiled execution, polygon generation, overlap resolution, and `.vzg` file update

### Why CellposeSAM?

CellposeSAM combines the Cellpose neural network with the Segment Anything Model
(SAM) encoder, delivering state-of-the-art segmentation accuracy without
manual tuning. Key advantages over earlier Cellpose versions:

- **Better generalization** — performs well on tissue types and staining
  patterns not seen during training
- **More robust boundaries** — SAM's visual encoder improves cell edge detection
  in crowded regions
- **Fewer hyperparameters** — default settings work out-of-the-box for most
  MERSCOPE experiments


## Requirements

| Requirement | Details |
|-------------|---------|
| **Python** | 3.9 or 3.10 (3.11+ not supported) |
| **OS** | Linux recommended; macOS/Windows may work but are untested |
| **GPU** | NVIDIA GPU with CUDA recommended; CPU fallback is slow (~10–50×) |
| **Disk** | ~2 GB for model weights (cached to `~/.cellpose/models/`) |
| **RAM** | 16 GB+ recommended for large tiles |


## Installation

Install VPT (the host CLI) **and** this plugin into the same Python environment:

```bash
pip install vpt
pip install vpt-plugin-cellposesam
```

Or install from source with Poetry:

```bash
pip install vpt                    # host CLI — required separately
git clone https://github.com/Vizgen/vpt-plugin-cellposesam-internal.git
cd vpt-plugin-cellposesam-internal
poetry install                     # installs the plugin + bundled CellposeSAM
```

Verify the installation:

```bash
vpt --help
```

### Bundled CellposeSAM code

This package includes a subset of the
[Cellpose v4 (CellposeSAM)](https://github.com/MouseLand/cellpose) codebase
(inference engine, dynamics, transforms, and the SAM-based model). The bundled
code is copyright Howard Hughes Medical Institute, authored by Carsen Stringer,
Michael Rariden, and Marius Pachitariu.


## Model Selection

The default model is `cpsam` (CellposeSAM), which downloads automatically
from Hugging Face on first use and is cached to `~/.cellpose/models/`. Set
the `CELLPOSE_LOCAL_MODELS_PATH` environment variable to override the cache
directory.

**`custom_weights`** overrides bundled model resolution entirely. When set, the
plugin loads the model from that path and ignores the default `cpsam` weights.

**`model_dimensions`** should be set to `"2D"` for MERSCOPE experiments.
Each z-plane is segmented independently. A `"3D"` mode exists but is **not
recommended** — it is significantly slower and has not been validated for
MERSCOPE data.


## Usage

VPT runs segmentation from a **segmentation specification JSON** that describes
experiment properties, input channels, model parameters, and output files.
The same spec run against multiple experiments ensures identical, reproducible
processing.

> **Coexistence with other Cellpose plugins:** The CellposeSAM plugin bundles
> its own copy of the Cellpose v4 inference code, so it can be installed
> alongside other Cellpose-based VPT plugins (e.g. Cellpose or Cellpose2)
> without dependency conflicts.

Working specs are provided in
[`example_analysis_algorithm/`](example_analysis_algorithm/):

| File | Dataset | Channels | Notes |
|------|---------|----------|-------|
| [`segmentation_specification.json`](example_analysis_algorithm/segmentation_specification.json) | Generic MERSCOPE | DAPI, PolyT, Cellbound3 | Default 2D template |
| [`U2OS_segmentation_specification.json`](example_analysis_algorithm/U2OS_segmentation_specification.json) | [U2OS_small_set](https://d21zg11mb7aqva.cloudfront.net/202305010900_U2OS_small_set_VMSC00000.zip) | DAPI, PolyT, Cellbound1 | 3-channel, 7 z-levels |

### Quick start

```bash
vpt --verbose run-segmentation \
  --segmentation-algorithm path/to/cellposesam_spec.json \
  --input-images 'path/to/images/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif' \
  --input-micron-to-mosaic path/to/micron_to_mosaic_pixel_transform.csv \
  --output-path output_dir/ \
  --tile-size 2400 \
  --tile-overlap 200
```

### Example: U2OS small dataset

The [U2OS_small_set](https://d21zg11mb7aqva.cloudfront.net/202305010900_U2OS_small_set_VMSC00000.zip)
is a public MERSCOPE dataset (3953 x 3960 px, 5 stains, 7 z-levels) suitable
for end-to-end verification. The example spec selects three of the five stains
(DAPI, PolyT, Cellbound1) and segments z-layer 3:

```bash
# Download and extract (~960 MB)
wget -q https://vzg-web-resources.s3.amazonaws.com/202305010900_U2OS_small_set_VMSC00000.zip
unzip -q 202305010900_U2OS_small_set_VMSC00000.zip

# Run segmentation
vpt --verbose run-segmentation \
  --segmentation-algorithm example_analysis_algorithm/U2OS_segmentation_specification.json \
  --input-images '202305010900_U2OS_small_set_VMSC00000/region_0/images/mosaic_(?P<stain>[\w|-]+)_z(?P<z>[0-9]+).tif' \
  --input-micron-to-mosaic 202305010900_U2OS_small_set_VMSC00000/region_0/images/micron_to_mosaic_pixel_transform.csv \
  --output-path u2os_output/ \
  --tile-size 2400 --tile-overlap 200
```

**Expected results:** ~5,500 cells across 4 tiles.  After completion the output
directory contains:

| File | Description |
|------|-------------|
| `result_tiles/` | Per-tile intermediate segmentation results |
| `cellpose_mosaic_space.parquet` | Cell boundary polygons in **mosaic pixel** coordinates |
| `cellpose_micron_space.parquet` | Cell boundary polygons in **micron** coordinates (transformed via `micron_to_mosaic_pixel_transform.csv`) |
| `cellpose_cell_metadata.csv` | Per-cell geometric metadata (area, centroid, bounding box) |


### Segmentation specification anatomy

For a full description of Cellpose model parameters, see the
[Cellpose documentation](https://cellpose.readthedocs.io/en/latest/).

A spec JSON has four top-level sections. The plugin only reads the
**bold** keys; the rest are consumed by VPT itself. For a complete description
of VPT-level parameters (`task_input_data`, `polygon_parameters`,
`segmentation_task_fusion`, `output_files`), see the
[VPT User Guide](https://vizgen.github.io/vizgen-postprocessing/).

```jsonc
{
  "experiment_properties": {            // VPT: z-index and z-position metadata
    "all_z_indexes": [0, 1, 2, ...],
    "z_positions_um": [1.5, 3.0, ...]
  },
  "segmentation_tasks": [
    {
      "task_id": 0,
      "segmentation_family": "CellposeSAM",  // VPT: selects this plugin
      "entity_types_detected": ["cell"],      // VPT: output entity type
      "z_layers": [3],                        // VPT: which z-planes to segment
      "segmentation_properties": {            // ** CellposeSAM plugin **
        "model": "cellpose-sam",
        "model_dimensions": "2D",
        "version": "latest",
        "custom_weights": null
      },
      "task_input_data": [ ... ],             // VPT: channel selection + preprocessing
      "segmentation_parameters": {            // ** CellposeSAM plugin **
        "nuclear_channel": "DAPI",
        "entity_fill_channel": "PolyT",
        "diameter": 30,
        "flow_threshold": 0.95,
        "cellprob_threshold": -5.5,
        "minimum_mask_size": 500
      },
      "polygon_parameters": { ... }           // VPT: mask-to-polygon conversion
    }
  ],
  "segmentation_task_fusion": { ... },  // VPT: multi-task entity fusion
  "output_files": [ ... ]              // VPT: output file paths
}
```

#### `segmentation_properties`

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `model` | `str` | **yes** | Model name (e.g. `"cellpose-sam"`) |
| `model_dimensions` | `str` | **yes** | `"2D"` or `"3D"` |
| `version` | `str` | **yes** | Model version (e.g. `"latest"`) |
| `custom_weights` | `str` or `null` | no | Path to a custom pretrained model. When set, overrides the default `cpsam` weights |

#### `segmentation_parameters`

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `nuclear_channel` | `str` | **yes** | Image channel name for the nuclear stain (e.g. `"DAPI"`). Must appear in `task_input_data` |
| `entity_fill_channel` | `str` | **yes** | Image channel name for the cell body stain (e.g. `"PolyT"`). Must appear in `task_input_data` |
| `diameter` | `int` | **yes** | Expected cell diameter in pixels. Typical values: 30 (standard cells) |
| `flow_threshold` | `float` | **yes** | Flow error threshold for mask filtering (e.g. `0.95`) |
| `cellprob_threshold` | `float` | **yes** | Cell probability threshold; lower values detect more cells (e.g. `-5.5`) |
| `minimum_mask_size` | `int` | **yes** | Minimum mask size in pixels; masks smaller than this are discarded (e.g. `500`) |

> **Note on channels:** When both `nuclear_channel` and `entity_fill_channel`
> are provided, the plugin stacks those two channels in order and passes them
> to the model. When either is empty/null, all channels from `task_input_data`
> are stacked instead.

> **Using membrane stains:** If your experiment includes a membrane marker
> (e.g. Cellbound1, Cellbound2, Cellbound3), prefer it over PolyT as the
> `entity_fill_channel` for sharper cell boundaries. To use three or more
> channels, set both `nuclear_channel` and `entity_fill_channel` to `null`
> and list all desired channels in `task_input_data`—they will be stacked
> automatically.

### Validation

The plugin validates the spec at task load time and will **fail fast** with a
`ValueError` if:

- `nuclear_channel` is specified but does not appear in `task_input_data` channels
- `entity_fill_channel` is specified but does not appear in `task_input_data` channels


## Limitations

- **GPU required for production use.** The plugin auto-detects GPU availability
  and falls back to CPU when no CUDA device is found. CPU mode works but is
  very slow (~10–50× slower) and is only suitable for small-scale testing. To
  force CPU mode on a GPU machine, set `CUDA_VISIBLE_DEVICES=""`.
- **Empty z-levels are skipped.** If all channels in a z-plane have near-zero
  variance (std < 0.1), that plane is filled with an empty mask.
- **3D mode is not recommended.** While the plugin accepts
  `model_dimensions: "3D"`, it is significantly slower and has not been
  validated for MERSCOPE data. Use `"2D"` for all production workflows.


## Troubleshooting

### Model download fails (proxy / air-gapped environment)

The `cpsam` weights are fetched from Hugging Face on first run. If you're
behind a corporate proxy or on an offline machine:

1. Download the model on a machine with internet access
2. Copy the `~/.cellpose/models/` directory to the target machine
3. Set `CELLPOSE_LOCAL_MODELS_PATH` to point to that directory

### CUDA out of memory

Reduce the tile size to lower GPU memory usage:

```bash
vpt run-segmentation ... --tile-size 1200 --tile-overlap 100
```

Typical memory usage: ~4 GB for 2400×2400 tiles, ~1.5 GB for 1200×1200 tiles.

### Segmentation is very slow

1. **Confirm GPU is detected** — Look for `Using GPU` in the verbose output.
   If you see `Using CPU`, check your CUDA installation.
2. **Check tile size** — Very large tiles (>4000 px) can slow down processing.
3. **Avoid 3D mode** — Use `model_dimensions: "2D"` for MERSCOPE data.

### No cells detected

- Lower `cellprob_threshold` (e.g., from `-5.5` to `-6.0` or `-7.0`)
- Verify that `nuclear_channel` and `entity_fill_channel` match channel names
  in your images (check `task_input_data` in the spec)
- Inspect input images to confirm staining is visible


## Documentation

- [VPT User Guide](https://vizgen.github.io/vizgen-postprocessing/)
- [Cellpose v4 (CellposeSAM) repository](https://github.com/MouseLand/cellpose)

### Citation

> Stringer, C. & Pachitariu, M. (2025). Cellpose-SAM: superhuman
> generalization for cellular segmentation. *bioRxiv*, 2025.04.28.651001.
> doi: [10.1101/2025.04.28.651001](https://doi.org/10.1101/2025.04.28.651001)

> Stringer, C., Wang, T., Michaelos, M., & Pachitariu, M. (2021). Cellpose:
> a generalist algorithm for cellular segmentation. *Nature Methods, 18*(1),
> 100–106.


## Feedback & Support

For bugs or feature requests **related to this plugin or VPT**, please
[open an issue](https://github.com/Vizgen/vizgen-postprocessing/issues) on the
VPT repository (covers all Vizgen VPT plugins). Include:

- A quick issue summary
- Steps to reproduce
- The exception / traceback, if applicable

For other questions, contact your regional Vizgen field application scientist
and CC Vizgen Tech Support at techsupport@vizgen.com (include "VPT" in the
subject line).


## Contributing & Code of Conduct

We welcome code contributions! Please refer to the [contribution guide](CONTRIBUTING.md) and
[code of conduct](CODE_OF_CONDUCT.md) before getting started.


## Authors

- [Vizgen](https://vizgen.com/)

![Logo](https://vizgen.com/wp-content/uploads/2022/12/Vizgen-Logo_Vizgen-BlackColor-.png)


## License

Copyright 2022 Vizgen, Inc. Licensed under the
[Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
See [LICENSE](LICENSE.md) for the full text.

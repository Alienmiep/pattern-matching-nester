## Installation Instructions

Dependency management is done with Poetry.

I personally use Poetry and Python's `venv` for installation:
```bash
python -m venv .venv
source .venv/Scripts/activate
poetry install
```

This does not include PyQt5, as it can't be installed via Poetry.

Install manually with pip while the virtual environment is active:
```bash
pip install PyQt5==5.15.11
```


## Running the Program

With the virtual environment active, run `demo.py` to launch the program.

```bash
python demo.py
```

To change out the pattern, modify `SVG_FILE` in `demo.py` to point to the correct file. Some example pattern files can be found in the `data` directory.

`fitted_skirt_with_seams.svg` and `turtleneck_with_seams.svg` work well with the algorithm, while `pants_with_seams.svg` is a good example for precision-related errors. Since `turtleneck_with_seams.svg` includes sleeves, `MERGE_SLEEVES` should be set to True.

Fabric parameters have to be saved with the "Apply" button before the fabric is updated.

## Repository Overview

Important files and directories:

```
|- data: Input SVG files
|- GarmentCode drop-ins: In version 1.0 of GarmentCode, replace wrappers.py with the version found in this directory to have GarmentCode output the seam information
|- pattern-matching-nester
|--- models
|----- pattern.py: Class that stores pattern information (pieces and seams)
|----- piece.py: Class that stores piece information, responsible for extracting the piece's vertices from SVG path
|--- demo.py: Main file, launches the GUI and contains the nesting algorithm
|--- ifp.py: Contains IFP generation
|--- nfp.py: Contains NFP generation
|- cutting_layout.svg: Cutting layout generated when the user clicks Export button
|- debug.png: Generated image showing the algorithm's inner state in case of an error in the NFP generation
|- experiment.py: Utility to view and modify SVG files. Can be used to easily add names to SVG paths.
|- nfp_standalone.py: Older version of NFP generation function used for development. Features more explanations about the NFP generation's inner workings than the current version.
|- seam_input.py: Command line tool for generating seam information for non-GarmentCode patterns.
```



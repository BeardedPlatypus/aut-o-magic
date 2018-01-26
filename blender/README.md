# Blender scripts

## [laser_cut_svg_export](https://github.com/BeardedPlatypus/aut-o-magic/blob/master/blender/lasercut_svg_export.py)

The laser cut script provides a method to quickly export flat objects to svg,
such that they can be laser cut. It does so based upon the `x` and `y` 
coordinates in 3d space.

### Usage

The script runs inside blender. It can be imported in the text-editor window,
from where it can be run. The variables in the main section can be adjusted to
select the proper 3d objects to be exported. 

Generated svg files are currently placed in the blender folder.

### Dependencies

This script needs to run inside a blender instance that has the python 
`svgwrite` module installed. This can be done by installing pip for the
python distribution that is bundled with python. Afterwards the bundled
python executable needs to execute a pip install for `svgwrite`

### Additional Notes

Currently this script does not support rotating and moving created svg shapes.
This will be added in the future. The script will hopefully get developed into
a proper add-on, which removes the need to install additional python modules.


from .acquisition import *
from .ancillary import *
from .brdf import *
from .calculate_lon_lat_arrays import *
from .data import *
from .dsm import *
from .endmembers import *
from .fc_utils import *
from .hdf5 import *
from .land_sea_masking import *
from .margins import *
from .metadata import *
from .modtran import *
from .modtran_profiles import *
from .mtl import *
from .tle import *

try:
    from __cast_shadow_mask import cast_shadow_main  # F2Py
    from __exiting_angle import exiting_angle  # F2Py
    from __incident_angle import incident_angle  # F2Py
    from __interpolation import bilinear  # F2Py
    from __sat_sol_angles import angle  # F2Py
    from __satellite_model import set_satmod  # F2Py
    from __slope_aspect import slope_aspect  # F2Py
    from __surface_reflectance import reflectance  # F2Py
    from __track_time_info import set_times  # F2Py

    from .calculate_angles import *
    from .calculate_incident_exiting_angles import *
    from .calculate_reflectance import calculate_reflectance
    from .calculate_shadow_masks import *
    from .calculate_slope_aspect import *
except ImportError:
    msg = (
        "FORTRAN modules have not been built.\n"
        "Some functionality in library is disabled"
    )
    print(msg)

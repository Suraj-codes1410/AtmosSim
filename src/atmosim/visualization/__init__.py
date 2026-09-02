"""
Visualization and diagnostic plotting module for AtmosSim.
"""

from atmosim.visualization.plume import (
    plot_plume_2d,
    plot_crosswind_slice,
    plot_downwind_centerline,
)
from atmosim.visualization.puff import (
    plot_puff_trajectories,
    plot_puff_dispersion_growth,
    plot_puff_concentration_field,
    plot_puff_lifecycle_dynamics,
)
from atmosim.visualization.environmental import (
    plot_meteorological_time_series,
    plot_source_network_and_terrain,
)

__all__ = [
    "plot_plume_2d",
    "plot_crosswind_slice",
    "plot_downwind_centerline",
    "plot_puff_trajectories",
    "plot_puff_dispersion_growth",
    "plot_puff_concentration_field",
    "plot_puff_lifecycle_dynamics",
    "plot_meteorological_time_series",
    "plot_source_network_and_terrain",
]

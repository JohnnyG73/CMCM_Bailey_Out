"""Parametric schematic geometry of Bailey Hall (meters, origin = semicircle center, +x E, +y N).

This module is only used to *generate the first draft* of data/nodes.csv and data/edges.csv.
After that, the CSVs are the single source of truth (edit them by hand or with the node editor).
All numbers below were read off the calibrated plans (see data/calibration.json); every one
that is not a printed dimension is an ESTIMATE and is listed in the README.
"""
import math

# ---------------------------------------------------------------- ring paths
# Corridor and portico are "stadium" paths: straight along each side wall for y in [0, y_north],
# a semicircle (center = origin) for y < 0. Position along the path is the arclength s measured
# from the north end of the WEST leg, so edge length = |s_u - s_v| = arc length on curved parts.

class RingPath:
    def __init__(self, r, y_north):
        self.r, self.yn = r, y_north
        self.L_leg = y_north
        self.L_arc = math.pi * r
        self.L = 2 * self.L_leg + self.L_arc

    def xy(self, s):
        r, yn = self.r, self.yn
        if s <= self.L_leg:                     # west leg, going south
            return -r, yn - s
        s2 = s - self.L_leg
        if s2 <= self.L_arc:                    # semicircle west -> south -> east
            th = math.pi + s2 / r               # pi (west) .. 2pi (east)
            return r * math.cos(th), r * math.sin(th)
        return r, s2 - self.L_arc               # east leg, going north

    def s_of_xy(self, x, y):
        """Arclength of the projection of (x, y) onto the path."""
        if y >= 0:
            yy = min(max(y, 0.0), self.yn)
            return (self.yn - yy) if x < 0 else (self.L_leg + self.L_arc + yy)
        th = math.atan2(y, x) % (2 * math.pi)   # in (pi, 2pi)
        return self.L_leg + (th - math.pi) * self.r


# corridor between loge back wall (r ~ 14.8 m) and portico wall (r ~ 18.1 m)
CORRIDOR = RingPath(r=16.5, y_north=10.5)
CORRIDOR_WIDTH = 3.3            # estimated
# outdoor portico between portico wall (18.1 m) and colonnade (20.5 m)
PORTICO = RingPath(r=19.3, y_north=10.5)
PORTICO_WIDTH = 2.4             # estimated

# ---------------------------------------------------------------- doors (west side; east = mirror)
R_LOGE_WALL = 14.8
MEZZ_DOORS_WEST = {             # id : (x, y)  -- door in the loge back wall
    "MD_W1": (-14.8, 9.8),      # north end of box rows
    "MD_W2": (-14.8, 4.3),      # end of box cross-aisle (between 100- and 200-series box seats)
    "MD_W3": (-14.3, -3.7),     # junction of box rows and curved loge rows (theta ~ 194 deg)
    "MD_W4": (-6.2, -13.4),     # end of loge radial aisle (theta ~ 245 deg)
}
MEZZ_DOOR_CENTER = ("MD_S", (0.0, -14.8))
MEZZ_DOOR_WIDTH = 1.7           # estimated (pair of leaves)

PORTICO_DOORS_WEST = {"PD_W1": (-18.1, 4.2), "PD_W2": (-15.7, -9.0)}
PORTICO_DOOR_WIDTH = 1.5        # estimated
PORTICO_STAIR_WEST = {"top": (-17.3, -11.0), "bottom": (-21.1, -11.8)}
PORTICO_STAIR = {"width": 2.0, "rise": 2.2}          # estimated

FOYER_DOORS = {"FD_W": (-3.3, -17.6), "FD_C": (0.0, -17.6), "FD_E": (3.3, -17.6)}
FOYER_DOOR_WIDTH = 1.8          # estimated
FOYER_NODES = {"F_W": (-4.0, -21.0), "F_C": (0.0, -21.0), "F_E": (4.0, -21.0)}
FOYER_EXT_DOORS_X = [-6.1, -3.05, 0.0, 3.05, 6.1]    # between the 6 entrance columns
FOYER_EXT_DOOR_Y = -24.7
FOYER_EXT_DOOR_WIDTH = 1.8      # estimated
MAIN_STAIR = {"top_y": -26.5, "bottom_y": -32.4, "rise": 2.2, "lane_width": 3.0}  # rise estimated

# ---------------------------------------------------------------- balcony circulation
BALC_WALKWAY_R = 17.0           # walkway behind the balcony columns (estimated)
BALC_FOYER_STAIR_WEST = {"top": (-8.4, -14.6), "bottom": (-6.6, -18.0)}   # stair 20001
BALC_FOYER_STAIR = {"lanes": 2, "lane_width": 1.1, "rise": 4.6, "run": 7.6, "landing": 1.5}
BALC_SIDE_STAIR_WEST = {"top": (-16.4, 8.6), "exit": (-19.2, 11.8)}       # stair at 20004
BALC_SIDE_STAIR = {"width": 1.2, "rise": 6.8, "run": 11.0, "landings": 4.0}

# ---------------------------------------------------------------- orchestra
ORCH_AISLE_X = 4.3              # two radial aisles at x = +/-4.3 m (page_3)
ORCH_BARRIER_R = 9.8            # orchestra / mezzanine barrier arc
ACCESS_POINTS_WEST = {          # 6 access points orchestra -> mezzanine (3 per side)
    "AP_W_front": (-8.8, 8.1),  # small stair at front corner by the stage
    "AP_W_mid": (-8.8, -2.6),   # stair at side, between box rows and curved loge
    "AP_W_back": (-4.0, -9.8),  # radial aisle steps up through the loge
}


def mirror(d):
    """West-side dict -> east-side dict (id W->E, x -> -x)."""
    out = {}
    for k, v in d.items():
        k2 = k.replace("_W", "_E")
        if isinstance(v, dict):
            out[k2] = {kk: (-vv[0], vv[1]) for kk, vv in v.items()}
        else:
            out[k2] = (-v[0], v[1])
    return out

"""Parametric schematic geometry of Bailey Hall (meters, origin = semicircle center, +x E, +y N).

Used only to generate the FIRST DRAFT of data/nodes.csv and data/edges.csv (src/generate_layout.py).
After that the CSVs are the single source of truth (edit by hand or with the node editor).
Values were read off the calibrated plans (data/calibration.json). Anything that is not a printed
dimension or a direct measurement is marked ESTIMATED here and listed in the README.
"""
import math

# ---------------------------------------------------------------- ring paths
class RingPath:
    """'Stadium' path: straight leg along each side wall for y in [0, y_north], semicircle about the
    origin for y < 0. s = arclength from the north end of the WEST leg; edge length = |ds|
    (= radius x angle on the curved part)."""

    def __init__(self, r, y_north):
        self.r, self.yn = r, y_north
        self.L_leg, self.L_arc = y_north, math.pi * r

    def xy(self, s):
        if s <= self.L_leg:
            return -self.r, self.yn - s
        s2 = s - self.L_leg
        if s2 <= self.L_arc:
            th = math.pi + s2 / self.r
            return self.r * math.cos(th), self.r * math.sin(th)
        return self.r, s2 - self.L_arc

    def s_of_xy(self, x, y):
        if y >= 0:
            yy = min(y, self.yn)
            return (self.yn - yy) if x < 0 else (self.L_leg + self.L_arc + yy)
        th = math.atan2(y, x) % (2 * math.pi)
        return self.L_leg + (th - math.pi) * self.r

    def s_of_deg(self, deg):
        return self.L_leg + math.radians(deg - 180) * self.r


def polar(r, deg):
    return r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))


# ------------------------------------------------------------------ level 1
CORRIDOR = RingPath(r=16.5, y_north=10.5)    # between loge back wall (14.8) and portico wall (18.1)
CORRIDOR_WIDTH = 3.3                         # measured on page_3 (approx.)
PORTICO = RingPath(r=19.3, y_north=10.5)     # outdoor portico, wall 18.1 .. colonnade 20.5
PORTICO_WIDTH = 2.4                          # measured on page_3 (approx.)

# Mezzanine doors in the loge back wall, west side (east = mirror). Each ends a loge cross-aisle.
MEZZ_DOORS_W = {
    "MD_W1": (-14.8, 9.8),    # north passage (north end of box rows)
    "MD_W2": (-14.8, 4.6),    # box cross-aisle between 100- and 200-series box seats
    "MD_W3": (-14.5, -3.0),   # junction aisle between box rows and curved loge (theta ~ 192 deg)
    "MD_W4": polar(14.8, 243),  # loge radial aisle between 300- and 400-series
}
MEZZ_DOOR_S = (0.0, -14.8)    # center south door, at the DD/EE wheelchair gap
MEZZ_DOOR_WIDTH = 1.7         # ESTIMATED

PORTICO_DOORS_W = {"PD_W1": (-18.1, 4.2), "PD_W2": polar(18.1, 210)}
PORTICO_DOOR_WIDTH = 1.5      # ESTIMATED
PORTICO_STAIR_W = {"top": polar(20.5, 212), "bottom": (-21.1, -11.8)}
PORTICO_STAIR_WIDTH = 2.0     # ESTIMATED
PORTICO_STAIR_RISE = 2.2      # ESTIMATED (same grade drop as the main entrance stair)

FOYER_DOORS = {"FD_W": (-3.3, -17.6), "FD_C": (0.0, -17.6), "FD_E": (3.3, -17.6)}
FOYER_DOOR_WIDTH = 1.8        # ESTIMATED
FOYER = {"F_W": (-4.0, -21.0), "F_C": (0.0, -21.0), "F_E": (4.0, -21.0)}
FOYER_EXT_X = [-6.1, -3.05, 0.0, 3.05, 6.1]  # 5 exterior doors between the 6 entrance columns
FOYER_EXT_Y = -24.7
FOYER_EXT_DOOR_WIDTH = 1.8    # ESTIMATED
MAIN_STAIR_BOTTOM_Y = -32.4
MAIN_STAIR_RISE = 2.2         # ESTIMATED (~13 risers x 0.17 m)
MAIN_STAIR_LANE_WIDTH = 3.0   # stair is ~15 m wide, split into 5 lanes in front of the 5 doors

# Orchestra
ORCH_ROWS = ["A","B","C","D","E","F","G","H","J","K","L","M","N","P","Q","R","S","T","U"]
ORCH_ROW_Y0, ORCH_ROW_PITCH = 6.4, 0.85       # row A at y=+6.4, row U at y=-8.9 (page_5)
ORCH_AISLE_X_FRONT, ORCH_AISLE_X_BACK = 4.5, 3.9  # radial aisles converge slightly (page_3)
ORCH_AISLE_WIDTH = 0.9        # measured on page_5 (approx.)
ORCH_FRONT_AISLE_Y = 7.3      # cross-aisle between row A and the stage
SIDE_FRONT_Y = (6.9, -1.6)    # 11 side rows (front group)
SIDE_REAR_Y = (-2.8, -8.4)    # 6 side rows (rear group)
ORCH_MID_PASSAGE_Y = -2.2     # gap between side front/rear groups -> mid access stair
SEAT_PITCH = 0.53             # mean chair width (19-22 in chairs)
ROW_CLEAR_WIDTH = 0.35        # ESTIMATED clear passage between rows
ACCESS_POINTS_W = {"AP_W_front": (-8.8, 8.1), "AP_W_mid": (-8.8, -2.6), "AP_W_back": polar(9.8, 246)}
ACCESS_STAIR_RISE = 0.9       # ESTIMATED rise orchestra floor -> first loge tier
ACCESS_STAIR_WIDTH = 1.1      # ESTIMATED

# Loge tiers k=1..5 (inner->outer) = curved rows AA..EE = box rows 5..1
LOGE_R = [10.7, 11.6, 12.5, 13.4, 14.2]       # curved rows (page_5)
BOX_X = [10.3, 11.3, 12.2, 13.2, 14.2]        # box rows (page_5); box row 5 is inner
LOGE_TIER_RISE = 0.30         # ESTIMATED step per tier
LOGE_NORTH_Y = 9.8            # north passage
BOX100_Y = (9.4, 5.3)         # 100-series box segment extent
LOGE_CROSS_Y = 4.9            # box cross-aisle, 4'-0" wide (printed)
BOX200_Y = (4.0, -1.6)
LOGE_JUNCTION_Y = -2.4        # aisle between box 200 rows and curved 300 rows, 4'-5" wide (printed)
LOGE_RADIAL_DEG = 242         # aisle between 300 and 400 sections (page_5: ~-62 deg east)
LOGE_CENTER_GAP = (0.0, -13.8)  # wheelchair gap in DD/EE at the centerline

# ------------------------------------------------------------------ level 2 (balcony)
BALC_R = [14.8, 15.7, 16.6]   # tiers AAA, BBB, CCC; straight rows at x = +/-r, curved at radius r
BALC_TIER_RISE = 0.45         # ESTIMATED
BALC_NORTH_Y = 10.6           # north end of straight rows
BALC_BREAK_Y = -1.2           # aisle between straight 100 rows and curved 200 rows
BALC_RADIAL_DEG = 227         # aisle between 200 and 300 sections (page_6)
BALC_AISLE_WIDTH = 0.9        # ESTIMATED
WALKWAY = RingPath(r=17.7, y_north=10.6)  # walkway behind the balcony columns
WALKWAY_WIDTH = 1.5           # ESTIMATED
BALC_FOYER_STAIR_W = {"top": polar(18.5, 242), "bottom": (-6.4, -19.4)}  # stair 20001 -> vestibule -> foyer
BALC_FOYER_STAIR = {"lane_width": 1.1, "rise": 4.6, "run": 7.6, "landing": 1.5}  # ESTIMATED
BALC_SIDE_STAIR_W = {"top": (-16.4, 8.6), "exit": (-19.2, 11.8)}   # stair at 20004 -> outside
BALC_SIDE_STAIR = {"width": 1.2, "rise": 6.8, "run": 11.0, "landings": 4.0}   # ESTIMATED

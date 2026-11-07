"""Pixel <-> world (meter) transforms for the plan images, driven by data/calibration.json."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CAL = json.loads((ROOT / "data/calibration.json").read_text())["pages"]
FLOOR_PAGE = {1: "page_3", 2: "page_4"}   # default background for each floor

def px_to_m(page, px, py):
    c = CAL[page]; R = np.array(c["R"], float); o = np.array(c["origin_px"], float)
    v = np.stack([np.asarray(px, float) - o[0], np.asarray(py, float) - o[1]])
    return tuple(c["m_per_px"] * (R @ v.reshape(2, -1)).reshape(v.shape))

def m_to_px(page, x, y):
    c = CAL[page]; Rinv = np.linalg.inv(np.array(c["R"], float)); o = np.array(c["origin_px"], float)
    v = np.stack([np.asarray(x, float), np.asarray(y, float)]) / c["m_per_px"]
    p = (Rinv @ v.reshape(2, -1)).reshape(v.shape)
    return p[0] + o[0], p[1] + o[1]

def extent_m(page, w=1700, h=2200):
    """Image extent in world meters for matplotlib imshow(extent=...) — valid for unrotated (R diagonal) pages."""
    x0, y0 = px_to_m(page, 0, 0); x1, y1 = px_to_m(page, w, h)
    return [float(x0), float(x1), float(y1), float(y0)]

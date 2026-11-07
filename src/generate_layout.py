"""Generate the first draft of the schematic walkable network from layout_geometry.py + data/seat_counts.csv.

    python src/generate_layout.py --preview   # writes results/proposal/{nodes,edges}.csv (default)
    python src/generate_layout.py --write     # writes data/nodes.csv, data/edges.csv (OVERWRITES hand edits!)

After the first --write, data/*.csv are the single source of truth; do not regenerate unless you
mean to discard hand corrections.
"""
import argparse
import math
from pathlib import Path

import pandas as pd

import layout_geometry as G

ROOT = Path(__file__).resolve().parents[1]
SIDES = {"W": -1, "E": +1}


class Net:
    def __init__(self):
        self.nodes, self.edges = {}, []

    def node(self, nid, typ, floor, x, y, section="", seats=0, notes=""):
        assert nid not in self.nodes, nid
        self.nodes[nid] = dict(id=nid, type=typ, floor=floor, x_m=round(x, 2), y_m=round(y, 2),
                               section=section, seats=int(seats), notes=notes)
        return nid

    def xy(self, n):
        return self.nodes[n]["x_m"], self.nodes[n]["y_m"]

    def dist(self, u, v):
        (x1, y1), (x2, y2) = self.xy(u), self.xy(v)
        return math.hypot(x2 - x1, y2 - y1)

    def edge(self, u, v, typ, width, notes="", length=None, rise=None):
        if length is None:
            length = self.dist(u, v)
            if rise is not None:                      # along-the-stair length
                length = math.hypot(length, rise)
        self.edges.append(dict(u=u, v=v, type=typ, length_m=round(length, 2), width_m=width, notes=notes))


def seat_table():
    return pd.read_csv(ROOT / "data/seat_counts.csv", dtype={"row": str})


def seats(tab, level, side, section, row):
    m = tab[(tab.level == level) & (tab.side == side) & (tab.section == section) & (tab.row == row)]
    assert len(m) == 1, (level, side, section, row)
    return int(m.seats.iloc[0])


def ring_chain(net, ring, node_ids, typ_note, width):
    """Connect nodes lying on a RingPath in order of arclength; length = |ds| (arc length)."""
    ordered = sorted(node_ids, key=lambda n: ring.s_of_xy(*net.xy(n)))
    for a, b in zip(ordered, ordered[1:]):
        L = abs(ring.s_of_xy(*net.xy(b)) - ring.s_of_xy(*net.xy(a)))
        net.edge(a, b, "level", width, f"{typ_note} arc", length=L)


def deg_of(x, y):
    return math.degrees(math.atan2(y, x)) % 360


def mir_deg(deg, sx):
    """Angle given for the WEST side (180..270) -> mirrored for east (sx=+1)."""
    return deg if sx < 0 else (540 - deg) % 360


def build():
    net, tab = Net(), seat_table()
    side_name = {"W": "west", "E": "east"}

    # ================================================================ ORCHESTRA (floor 1)
    rows = G.ORCH_ROWS
    row_y = {r: G.ORCH_ROW_Y0 - i * G.ORCH_ROW_PITCH for i, r in enumerate(rows)}

    def aisle_x(y):
        f = (G.ORCH_ROW_Y0 - y) / (G.ORCH_ROW_Y0 - row_y["U"])
        return G.ORCH_AISLE_X_FRONT + f * (G.ORCH_AISLE_X_BACK - G.ORCH_AISLE_X_FRONT)

    pairs = [rows[i:i + 2] for i in range(0, len(rows), 2)]          # aisle node every 2 rows
    pair_of = {r: k for k, p in enumerate(pairs) for r in p}
    for S, sx in SIDES.items():
        prev = None
        for k, p in enumerate(pairs):
            y = sum(row_y[r] for r in p) / len(p)
            n = net.node(f"OA_{S}_{k:02d}", "aisle", 1, sx * aisle_x(y), y, "orch_aisle",
                         notes=f"{side_name[S]} radial aisle at rows {'/'.join(p)}")
            if prev:
                net.edge(prev, n, "level", G.ORCH_AISLE_WIDTH, "orchestra radial aisle; width estimated")
            prev = n
        net.node(f"OF_{S}", "aisle", 1, sx * aisle_x(G.ORCH_FRONT_AISLE_Y), G.ORCH_FRONT_AISLE_Y,
                 "orch_aisle", notes="front cross-aisle at head of radial aisle")
        net.edge(f"OF_{S}", f"OA_{S}_00", "level", G.ORCH_AISLE_WIDTH, "orchestra radial aisle")
        net.node(f"OM_{S}", "aisle", 1, sx * 7.0, G.ORCH_MID_PASSAGE_Y, "orch_aisle",
                 notes="mid passage between side front/rear groups")
        net.edge(f"OM_{S}", f"OA_{S}_{pair_of['L']:02d}", "level", 1.0, "mid passage; width estimated")
    net.edge("OF_W", "OF_E", "level", 1.5, "front cross-aisle below stage; width estimated")

    for r in rows:   # center section, one node per row, exits to both radial aisles
        n = net.node(f"OC_{r}", "row_segment", 1, 0.0, row_y[r], "orch_center",
                     seats(tab, "orchestra", "center", "orch_center", r), f"row {r}")
        for S in SIDES:
            net.edge(n, f"OA_{S}_{pair_of[r]:02d}", "row", G.ROW_CLEAR_WIDTH, "center row; clear width estimated")

    for S, sx in SIDES.items():   # side sections, exit only to the radial aisle
        side = side_name[S]
        for grp, (y0, y1), rlist in [("orch_side_front", G.SIDE_FRONT_Y, rows[:11]),
                                     ("orch_side_rear", G.SIDE_REAR_Y, rows[11:17])]:
            for i, r in enumerate(rlist):
                y = y0 + (y1 - y0) * i / (len(rlist) - 1)
                n_seats = seats(tab, "orchestra", side, grp, r)
                L = n_seats * G.SEAT_PITCH
                n = net.node(f"OS_{S}_{r}", "row_segment", 1, sx * (aisle_x(y) + 0.3 + L / 2), y, grp,
                             n_seats, f"side row ~{r} (letter inferred)")
                net.edge(n, f"OA_{S}_{pair_of[r]:02d}", "row", G.ROW_CLEAR_WIDTH, "side row; clear width estimated")

    # ================================================================ ACCESS POINTS + LOGE (floor 1)
    for S, sx in SIDES.items():
        side = side_name[S]
        for nid, (x, y) in G.ACCESS_POINTS_W.items():
            net.node(nid.replace("_W", f"_{S}"), "access_point", 1, sx * -x, y, "barrier",
                     notes="orchestra->mezzanine access stair; rise estimated")
        net.edge(f"OF_{S}", f"AP_{S}_front", "level", 1.5, "front cross-aisle")
        net.edge(f"OM_{S}", f"AP_{S}_mid", "level", 1.0, "mid passage")
        net.edge(f"OA_{S}_{len(pairs) - 1:02d}", f"AP_{S}_back", "level", G.ORCH_AISLE_WIDTH, "end of radial aisle")

        # tier aisle nodes k = 1..5
        rad = mir_deg(G.LOGE_RADIAL_DEG, sx)
        for k in range(1, 6):
            bx, r = G.BOX_X[k - 1], G.LOGE_R[k - 1]
            rj = (bx + r) / 2
            net.node(f"LN_{S}{k}", "aisle", 1, sx * bx, G.LOGE_NORTH_Y, "loge_aisle", notes=f"north passage, tier {k}")
            net.node(f"LX_{S}{k}", "aisle", 1, sx * bx, G.LOGE_CROSS_Y, "loge_aisle", notes=f"box cross-aisle (4'-0\"), tier {k}")
            net.node(f"LJ_{S}{k}", "aisle", 1, sx * math.sqrt(rj ** 2 - G.LOGE_JUNCTION_Y ** 2), G.LOGE_JUNCTION_Y,
                     "loge_aisle", notes=f"junction aisle (4'-5\"), tier {k}")
            x, y = G.polar(r, rad)
            net.node(f"LR_{S}{k}", "aisle", 1, x, y, "loge_aisle", notes=f"radial aisle 300|400, tier {k}")
        for a in "NXJR":
            for k in range(1, 5):
                w = {"N": 1.2, "X": 1.22, "J": 1.35, "R": 1.0}[a]
                net.edge(f"L{a}_{S}{k}", f"L{a}_{S}{k + 1}", "stair", w,
                         "stepped loge aisle; tier rise estimated" + ("" if a in "XJ" else "; width estimated"),
                         rise=G.LOGE_TIER_RISE)
        # access stairs up from the orchestra
        net.edge(f"AP_{S}_front", f"LN_{S}1", "stair", G.ACCESS_STAIR_WIDTH, "access stair; estimated", rise=G.ACCESS_STAIR_RISE)
        net.edge(f"AP_{S}_mid", f"LJ_{S}1", "stair", G.ACCESS_STAIR_WIDTH, "access stair; estimated", rise=G.ACCESS_STAIR_RISE)
        net.edge(f"AP_{S}_back", f"LR_{S}1", "stair", G.ACCESS_STAIR_WIDTH, "access stair; estimated", rise=G.ACCESS_STAIR_RISE)

        # box rows (straight, N-S); box row number 1 = wall = tier 5
        for k in range(1, 6):
            box = 6 - k
            bx = sx * G.BOX_X[k - 1]
            n1 = net.node(f"LB1_{S}{box}", "row_segment", 1, bx, sum(G.BOX100_Y) / 2, "loge_box_100",
                          seats(tab, "loge", side, "loge_box_100", str(box)), f"box row {box} (1 = wall), 100-series")
            n2 = net.node(f"LB2_{S}{box}", "row_segment", 1, bx, sum(G.BOX200_Y) / 2, "loge_box_200",
                          seats(tab, "loge", side, "loge_box_200", str(box)), f"box row {box} (1 = wall), 200-series")
            for a, b in [(n1, f"LN_{S}{k}"), (n1, f"LX_{S}{k}"), (n2, f"LX_{S}{k}"), (n2, f"LJ_{S}{k}")]:
                net.edge(a, b, "row", G.ROW_CLEAR_WIDTH, "box row; clear width estimated")

        # curved 300 rows: from junction aisle to radial aisle
        for k, lab in enumerate(["AA", "BB", "CC", "DD", "EE"], start=1):
            r = G.LOGE_R[k - 1]
            d0 = deg_of(*net.xy(f"LJ_{S}{k}"))
            dm = (d0 + rad) / 2          # both angles lie in 180..270 (W) or 270..360 (E)
            x, y = G.polar(r, dm)
            n = net.node(f"L3_{S}_{lab}", "row_segment", 1, x, y, "loge_curve_300",
                         seats(tab, "loge", side, "loge_curve_300", lab), f"row {lab}")
            half = r * math.radians(abs(((d0 - rad + 180) % 360) - 180)) / 2
            net.edge(n, f"LJ_{S}{k}", "row", G.ROW_CLEAR_WIDTH, "curved row (arc); clear width estimated", length=half)
            net.edge(n, f"LR_{S}{k}", "row", G.ROW_CLEAR_WIDTH, "curved row (arc); clear width estimated", length=half)

    # center 400 rows: AA-CC continuous between the two radial aisles; DD/EE split at the CL gap
    radW, radE = G.LOGE_RADIAL_DEG, mir_deg(G.LOGE_RADIAL_DEG, 1)
    net.node("LC", "aisle", 1, *G.LOGE_CENTER_GAP, "loge_aisle", notes="wheelchair gap in DD/EE at CL")
    for k, lab in enumerate(["AA", "BB", "CC", "DD", "EE"], start=1):
        r = G.LOGE_R[k - 1]
        if k <= 3:
            n = net.node(f"L4_{lab}", "row_segment", 1, 0.0, -r, "loge_center_400",
                         seats(tab, "loge", "center", "loge_center_400", lab), f"row {lab}")
            half = r * math.radians(radE - radW) / 2
            for S in SIDES:
                net.edge(n, f"LR_{S}{k}", "row", G.ROW_CLEAR_WIDTH, "curved row (arc); clear width estimated", length=half)
        else:
            for S, sx in SIDES.items():
                dm = (radW + 270) / 2 if sx < 0 else (270 + radE) / 2
                x, y = G.polar(r, dm)
                n = net.node(f"L4_{S}_{lab}", "row_segment", 1, x, y, "loge_center_400",
                             seats(tab, "loge", side_name[S], "loge_center_400", lab), f"row {lab}, {side_name[S]} half")
                half = r * math.radians(270 - radW) / 2
                net.edge(n, f"LR_{S}{k}", "row", G.ROW_CLEAR_WIDTH, "curved row (arc); clear width estimated", length=half)
                net.edge(n, "LC", "row", G.ROW_CLEAR_WIDTH, "curved row (arc) to CL gap", length=half)

    # ================================================================ DOORS, CORRIDOR, PORTICO, FOYER
    corridor_nodes = []

    def corridor_node(nid, x, y, note):
        s = G.CORRIDOR.s_of_xy(x, y)
        cx, cy = G.CORRIDOR.xy(s)
        corridor_nodes.append(net.node(nid, "corridor", 1, cx, cy, "corridor", notes=note))
        return nid

    for S, sx in SIDES.items():
        for nid, (x, y) in G.MEZZ_DOORS_W.items():
            d = net.node(nid.replace("_W", f"_{S}"), "mezz_door", 1, sx * -x, y, "loge_wall",
                         notes="mezzanine exit door; width estimated")
            c = corridor_node(d.replace("MD_", "C_MD_"), sx * -x, y, f"corridor at {d}")
            net.edge(d, c, "level", G.MEZZ_DOOR_WIDTH, "door -> corridor; width estimated")
        net.edge(f"LN_{S}5", f"MD_{S}1", "level", 1.2, "north passage -> door")
        net.edge(f"LX_{S}5", f"MD_{S}2", "level", 1.22, "cross-aisle -> door")
        net.edge(f"LJ_{S}5", f"MD_{S}3", "level", 1.35, "junction aisle -> door")
        net.edge(f"LR_{S}5", f"MD_{S}4", "level", 1.0, "radial aisle -> door")
    net.node("MD_S", "mezz_door", 1, *G.MEZZ_DOOR_S, "loge_wall", notes="center mezzanine exit door; width estimated")
    net.edge("LC", "MD_S", "level", 1.5, "CL gap -> center door")
    corridor_node("C_MD_S", *G.MEZZ_DOOR_S, "corridor at MD_S")
    net.edge("MD_S", "C_MD_S", "level", G.MEZZ_DOOR_WIDTH, "door -> corridor; width estimated")

    for nid, (x, y) in G.FOYER_DOORS.items():
        net.node(nid, "foyer_door", 1, x, y, "corridor_wall", notes="corridor -> foyer door; width estimated")
        c = corridor_node(f"C_{nid}", x, y, f"corridor at {nid}")
        net.edge(c, nid, "level", G.FOYER_DOOR_WIDTH, "corridor -> foyer door; width estimated")
    for nid, (x, y) in G.FOYER.items():
        net.node(nid, "foyer", 1, x, y, "foyer")
    net.edge("F_W", "F_C", "level", 6.0, "foyer"); net.edge("F_C", "F_E", "level", 6.0, "foyer")
    for d, f in [("FD_W", "F_W"), ("FD_W", "F_C"), ("FD_C", "F_C"), ("FD_E", "F_E"), ("FD_E", "F_C")]:
        net.edge(d, f, "level", G.FOYER_DOOR_WIDTH, "foyer")
    for i, x in enumerate(G.FOYER_EXT_X, start=1):
        top = net.node(f"ST_main{i}", "stair_top", 1, x, G.FOYER_EXT_Y, "main_stair",
                       notes="foyer exterior door + top of monumental stair (building envelope)")
        ex = net.node(f"EX_main{i}", "exit", 1, x, G.MAIN_STAIR_BOTTOM_Y, "street", notes="foot of monumental stair")
        f = "F_W" if x < -1 else ("F_E" if x > 1 else "F_C")
        net.edge(f, top, "level", G.FOYER_EXT_DOOR_WIDTH, "foyer -> exterior door; width estimated")
        net.edge(top, ex, "stair", G.MAIN_STAIR_LANE_WIDTH, "monumental stair lane; rise estimated", rise=G.MAIN_STAIR_RISE)

    portico_nodes = []
    for S, sx in SIDES.items():
        for nid, (x, y) in G.PORTICO_DOORS_W.items():
            d = net.node(nid.replace("_W", f"_{S}"), "portico_door", 1, sx * -x, y, "corridor_wall",
                         notes="corridor -> portico side door (rarely used); width estimated")
            c = corridor_node(d.replace("PD_", "C_PD_"), sx * -x, y, f"corridor at {d}")
            net.edge(c, d, "level", G.PORTICO_DOOR_WIDTH, "corridor -> portico door; width estimated")
            s = G.PORTICO.s_of_xy(sx * -x, y)
            p = net.node(d.replace("PD_", "P_"), "portico", 1, *G.PORTICO.xy(s), "portico", notes="outdoor portico")
            portico_nodes.append(p)
            net.edge(d, p, "level", G.PORTICO_DOOR_WIDTH, "door -> portico")
        tx, ty = G.PORTICO_STAIR_W["top"]; bx, by = G.PORTICO_STAIR_W["bottom"]
        top = net.node(f"ST_port_{S}", "stair_top", 1, sx * -tx, ty, "portico_stair", notes="top of portico side stair")
        portico_nodes.append(top)
        ex = net.node(f"EX_port_{S}", "exit", 1, sx * -bx, by, "street", notes="foot of portico side stair")
        net.edge(top, ex, "stair", G.PORTICO_STAIR_WIDTH, "portico stair; width & rise estimated", rise=G.PORTICO_STAIR_RISE)
    ring_chain(net, G.CORRIDOR, corridor_nodes, "corridor", G.CORRIDOR_WIDTH)
    for S in SIDES:   # portico: door1 - door2 - stair top (only the west/east arcs are connected)
        ring_chain(net, G.PORTICO, [f"P_{S}1", f"P_{S}2", f"ST_port_{S}"], "portico", G.PORTICO_WIDTH)

    # ================================================================ BALCONY (floor 2)
    walk = []
    for S, sx in SIDES.items():
        side = side_name[S]
        rad = mir_deg(G.BALC_RADIAL_DEG, sx)
        for t, lab in enumerate(["AAA", "BBB", "CCC"], start=1):
            r = G.BALC_R[t - 1]
            net.node(f"BN_{S}{t}", "aisle", 2, sx * r, G.BALC_NORTH_Y, "balc_aisle", notes=f"north end of straight row {lab}")
            net.node(f"BA_{S}{t}", "aisle", 2, sx * r, G.BALC_BREAK_Y, "balc_aisle", notes=f"aisle straight|curve, {lab}")
            net.node(f"BR_{S}{t}", "aisle", 2, *G.polar(r, rad), "balc_aisle", notes=f"radial aisle 200|300, {lab}")
            if S == "W":
                net.node(f"BC{t}", "aisle", 2, 0.0, -r, "balc_aisle", notes=f"centerline aisle, {lab}")
        for a in ["BN", "BA", "BR"] + (["BC"] if S == "W" else []):
            for t in (1, 2):
                u, v = (f"{a}_{S}{t}", f"{a}_{S}{t + 1}") if a != "BC" else (f"BC{t}", f"BC{t + 1}")
                net.edge(u, v, "stair", G.BALC_AISLE_WIDTH, "stepped balcony aisle; rise & width estimated", rise=G.BALC_TIER_RISE)
        for t, lab in enumerate(["AAA", "BBB", "CCC"], start=1):
            r = G.BALC_R[t - 1]
            n = net.node(f"B1_{S}_{lab}", "row_segment", 2, sx * r, (G.BALC_NORTH_Y + G.BALC_BREAK_Y) / 2,
                         "balc_straight_100", seats(tab, "balcony", side, "balc_straight_100", lab), f"row {lab}")
            for b in (f"BN_{S}{t}", f"BA_{S}{t}"):
                net.edge(n, b, "row", G.ROW_CLEAR_WIDTH, "straight row; clear width estimated")
            d0 = deg_of(*net.xy(f"BA_{S}{t}"))
            for sec, da, db, ea, eb in [("balc_curve_200", d0, rad, f"BA_{S}{t}", f"BR_{S}{t}"),
                                        ("balc_curve_300", rad, 270, f"BR_{S}{t}", f"BC{t}")]:
                dm = ((da + db) / 2) if sx < 0 else (((da if da > 180 else da + 360) + db) / 2) % 360
                n = net.node(f"{'B2' if '200' in sec else 'B3'}_{S}_{lab}", "row_segment", 2, *G.polar(r, dm), sec,
                             seats(tab, "balcony", side, sec, lab), f"row {lab}")
                half = r * math.radians(abs(((da - db + 180) % 360) - 180)) / 2
                for e in (ea, eb):
                    net.edge(n, e, "row", G.ROW_CLEAR_WIDTH, "curved row (arc); clear width estimated", length=half)
        # walkway behind columns
        for a in ("BN", "BA", "BR"):
            x, y = net.xy(f"{a}_{S}3")
            w = net.node(f"BW_{S}_{a[1]}", "aisle", 2, *G.WALKWAY.xy(G.WALKWAY.s_of_xy(x, y)), "balc_walkway",
                         notes="walkway behind balcony columns")
            walk.append(w)
            net.edge(f"{a}_{S}3", w, "level", G.BALC_AISLE_WIDTH, "aisle -> walkway")
        # foyer stair (two lanes split by a barrier)
        tx, ty = G.BALC_FOYER_STAIR_W["top"]; bx, by = G.BALC_FOYER_STAIR_W["bottom"]
        w = net.node(f"BW_{S}_F", "aisle", 2, *G.WALKWAY.xy(G.WALKWAY.s_of_xy(sx * -tx, ty)), "balc_walkway",
                     notes="walkway at foyer-stair door")
        walk.append(w)
        P = G.BALC_FOYER_STAIR
        L = 2 * math.hypot(P["run"] / 2, P["rise"] / 2) + P["landing"]
        for lane, off in (("a", -0.6), ("b", 0.6)):
            top = net.node(f"BS_{S}{lane}_top", "stair_top", 2, sx * -tx + off, ty, "balc_foyer_stair",
                           notes=f"balcony->foyer stair, lane {lane} (barrier splits 2 lanes)")
            bot = net.node(f"BS_{S}{lane}_bot", "stair_bottom", 1, sx * -bx + off, by, "balc_foyer_stair",
                           notes=f"lands in vestibule next to foyer, lane {lane}")
            net.edge(w, top, "level", P["lane_width"], "walkway -> stair lane")
            net.edge(top, bot, "stair", P["lane_width"], "2 flights + landing; run, rise, width estimated", length=L)
            net.edge(bot, f"F_{S}", "level", P["lane_width"], "vestibule -> foyer")
        # side stair near the stage, directly outside
        tx, ty = G.BALC_SIDE_STAIR_W["top"]; ex_, ey = G.BALC_SIDE_STAIR_W["exit"]
        P = G.BALC_SIDE_STAIR
        top = net.node(f"BSS_{S}_top", "stair_top", 2, sx * -tx, ty, "balc_side_stair", notes="emergency stair by stage")
        ex = net.node(f"EX_balc_{S}", "exit", 1, sx * -ex_, ey, "street", notes="foot of balcony side stair (ground)")
        net.edge(f"BW_{S}_N", top, "level", 1.2, "walkway -> side stair")
        net.edge(top, ex, "stair", P["width"], "balcony->ground, ~1.5 storeys; run, rise, landings estimated",
                 length=math.hypot(P["run"], P["rise"]) + P["landings"])
    wS = net.node("BW_S", "aisle", 2, *G.WALKWAY.xy(G.WALKWAY.s_of_deg(270)), "balc_walkway", notes="walkway at CL")
    walk.append(wS)
    net.edge("BC3", wS, "level", G.BALC_AISLE_WIDTH, "aisle -> walkway")
    ring_chain(net, G.WALKWAY, walk, "walkway", G.WALKWAY_WIDTH)

    nodes = pd.DataFrame(net.nodes.values())
    edges = pd.DataFrame(net.edges)
    return nodes, edges


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write data/nodes.csv & data/edges.csv")
    a = ap.parse_args()
    nodes, edges = build()
    out = ROOT / ("data" if a.write else "results/proposal")
    out.mkdir(parents=True, exist_ok=True)
    nodes.to_csv(out / "nodes.csv", index=False)
    edges.to_csv(out / "edges.csv", index=False)
    print(f"{len(nodes)} nodes, {len(edges)} edges -> {out.relative_to(ROOT)}")
    print(nodes.groupby("type").size().to_string())
    print(nodes.assign(level=nodes.section.str.split("_").str[0]).query("seats>0").groupby("level").seats.sum().to_string())

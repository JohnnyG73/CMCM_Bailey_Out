"""Render every page of the problem PDF to PNG (figures/plans/page_N.png)."""
import sys
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]

def render(pdf=ROOT / "CMCM_2026_Bail_ey_ing_Out.pdf", dpi=200, out=ROOT / "figures/plans"):
    out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    paths = []
    for i, page in enumerate(doc):
        p = out / f"page_{i+1}.png"
        page.get_pixmap(dpi=dpi).save(p)   # honors /Rotate, so rotated pages render as displayed
        paths.append(p)
        print(p.relative_to(ROOT), page.rotation)
    return paths

if __name__ == "__main__":
    render(dpi=int(sys.argv[1]) if len(sys.argv) > 1 else 200)

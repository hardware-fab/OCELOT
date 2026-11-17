from pathlib import Path
import gdspy

def compute_layout_area_um2(gds_path) -> float | None:
    p = Path(gds_path)
    if not p.exists():
        return None
    lib = gdspy.GdsLibrary(infile=str(p))
    xs, ys = ([], [])
    for cell in lib.cells.values():
        for poly in cell.get_polygons():
            xs.extend(poly[:, 0].tolist())
            ys.extend(poly[:, 1].tolist())
    if not xs:
        return None
    return float((max(xs) - min(xs)) * (max(ys) - min(ys)))

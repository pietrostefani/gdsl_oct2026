"""
Prepare routes and photos for the GDSL away day map.

Input:
  raw/routes/  one file per person: .geojson / .json / .gpx / .kml
               file name = person's name, e.g. "Carmen Cabrera.geojson"
  raw/photos/  one photo per person, same name as the route file, e.g. "Carmen Cabrera.jpg"
  raw/captions.csv (optional) columns: name, caption, lat, lon
               lat/lon override the photo position if the photo has no GPS.

Output:
  data/routes.geojson   one LineString per person (ends trimmed for privacy)
  data/photos.geojson   one point per photo, with caption and image path
  data/photos/*.jpg     resized photos with ALL metadata (EXIF/GPS) removed

Run:  python prep.py
"""
import csv
import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
from PIL import Image, ImageOps
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, substring

ROOT = Path(__file__).parent
RAW_ROUTES = ROOT / "raw" / "routes"
RAW_PHOTOS = ROOT / "raw" / "photos"
OUT = ROOT / "data"
OUT_PHOTOS = OUT / "photos"
TRIM_M = 150          # metres trimmed from each end of a route (privacy)
PHOTO_PX = 1200       # longest side of published photos
METRIC = 27700        # British National Grid, for lengths and trimming

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def person_name(path: Path) -> str:
    """'carmen_cabrera-route.geojson' -> 'Carmen Cabrera'."""
    stem = re.sub(r"(?i)[-_ ]?(route|path|walk|commute|photo|pic)$", "", path.stem)
    return re.sub(r"[_\-]+", " ", stem).strip().title()


def read_route(path: Path):
    ext = path.suffix.lower()
    if ext == ".gpx":
        frames = []
        for layer in ("tracks", "routes"):
            try:
                g = gpd.read_file(path, layer=layer)
                if len(g):
                    frames.append(g)
            except Exception:
                pass
        gdf = pd.concat(frames) if frames else gpd.GeoDataFrame()
    elif ext == ".kml":
        gdf = gpd.read_file(path, driver="KML")
    else:
        gdf = gpd.read_file(path)
    if gdf.empty:
        return None
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    lines = []
    for geom in gdf.geometry:
        if geom is None:
            continue
        if geom.geom_type == "LineString":
            lines.append(geom)
        elif geom.geom_type == "MultiLineString":
            lines.extend(geom.geoms)
        elif geom.geom_type in ("Polygon",):
            lines.append(LineString(geom.exterior.coords))
    if not lines:
        # points only (e.g. GPX waypoints): join them in order
        pts = [g for g in gdf.geometry if g is not None and g.geom_type == "Point"]
        if len(pts) >= 2:
            lines = [LineString([(p.x, p.y) for p in pts])]
    if not lines:
        return None
    merged = linemerge(MultiLineString(lines)) if len(lines) > 1 else lines[0]
    if merged.geom_type == "MultiLineString":   # disconnected pieces: keep the longest
        merged = max(merged.geoms, key=lambda l: l.length)
    # drop Z / M values
    return LineString([(c[0], c[1]) for c in merged.coords])


def trim(line_wgs84: LineString):
    """Remove TRIM_M metres from each end; return (trimmed line in 4326, length km)."""
    g = gpd.GeoSeries([line_wgs84], crs=4326).to_crs(METRIC)
    line = g.iloc[0]
    length = line.length
    if length > 4 * TRIM_M:
        line = substring(line, TRIM_M, length - TRIM_M)
    out = gpd.GeoSeries([line], crs=METRIC).to_crs(4326).iloc[0]
    return out, round(length / 1000, 1)


def exif_gps(img: Image.Image):
    try:
        gps = img.getexif().get_ifd(0x8825)
        if not gps:
            return None
        def dec(v, ref):
            d, m, s = [float(x) for x in v]
            val = d + m / 60 + s / 3600
            return -val if ref in ("S", "W") else val
        return dec(gps[2], gps[1]), dec(gps[4], gps[3])   # lat, lon
    except Exception:
        return None


def load_captions():
    path = ROOT / "raw" / "captions.csv"
    out = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                key = (row.get("name") or "").strip().title()
                if key:
                    out[key] = row
    return out


def main():
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass

    OUT_PHOTOS.mkdir(parents=True, exist_ok=True)
    for old in OUT_PHOTOS.glob("*"):
        old.unlink()
    captions = load_captions()

    # ---- routes
    routes, problems = [], []
    for path in sorted(RAW_ROUTES.glob("*")):
        if path.suffix.lower() not in {".geojson", ".json", ".gpx", ".kml"}:
            continue
        name = person_name(path)
        try:
            line = read_route(path)
        except Exception as e:
            problems.append(f"{path.name}: could not read ({e})")
            continue
        if line is None or len(line.coords) < 2:
            problems.append(f"{path.name}: no line found")
            continue
        line, km = trim(line)
        routes.append({"name": name, "km": km, "geometry": line})
    routes_gdf = gpd.GeoDataFrame(routes, geometry="geometry", crs=4326) if routes \
        else gpd.GeoDataFrame({"name": [], "km": []}, geometry=[], crs=4326)
    routes_gdf = routes_gdf.sort_values("name").reset_index(drop=True)

    # ---- photos
    photos = []
    by_name = {r["name"]: r["geometry"] for r in routes}
    for path in sorted(RAW_PHOTOS.glob("*")):
        if path.suffix.lower() not in PHOTO_EXT:
            continue
        name = person_name(path)
        try:
            img = Image.open(path)
        except Exception as e:
            problems.append(f"{path.name}: could not open photo ({e})")
            continue
        gps = exif_gps(img)
        cap = captions.get(name, {})
        if cap.get("lat") and cap.get("lon"):
            gps = (float(cap["lat"]), float(cap["lon"]))
        if gps is None and name in by_name:
            mid = by_name[name].interpolate(0.5, normalized=True)
            gps, placed = (mid.y, mid.x), "route midpoint"
        else:
            placed = "photo GPS" if gps else None
        if gps is None:
            problems.append(f"{path.name}: no location and no route to place it on")
            continue
        # clean copy: orientation applied, metadata dropped, resized
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((PHOTO_PX, PHOTO_PX))
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        out_path = OUT_PHOTOS / f"{slug}.jpg"
        img.save(out_path, "JPEG", quality=82, optimize=True)   # no exif= -> no metadata
        photos.append({
            "name": name,
            "caption": (cap.get("caption") or "").strip(),
            "img": f"data/photos/{slug}.jpg",
            "placed": placed,
            "geometry": Point(gps[1], gps[0]),
        })
    photos_gdf = gpd.GeoDataFrame(photos, geometry="geometry", crs=4326) if photos \
        else gpd.GeoDataFrame({"name": []}, geometry=[], crs=4326)

    routes_gdf.to_file(OUT / "routes.geojson", driver="GeoJSON")
    photos_gdf.to_file(OUT / "photos.geojson", driver="GeoJSON")

    print(f"Routes: {len(routes_gdf)} | Photos: {len(photos_gdf)}")
    have_route = set(routes_gdf["name"]) if len(routes_gdf) else set()
    have_photo = set(photos_gdf["name"]) if len(photos_gdf) else set()
    for n in sorted(have_route - have_photo):
        print(f"  route but no photo: {n}")
    for n in sorted(have_photo - have_route):
        print(f"  photo but no route: {n}")
    for p in problems:
        print(f"  PROBLEM {p}")


if __name__ == "__main__":
    main()

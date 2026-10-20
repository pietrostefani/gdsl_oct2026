# GDSL Away Day — 21 October 2026

Quarto website: agenda, "Our Liverpool" route map, and world café tables with Padlet links.
Published with GitHub Pages from the `docs/` folder on `main`.

## Update the map
1. Put route files in `raw/routes/` and photos in `raw/photos/`, each named after the person
   (e.g. `Carmen Cabrera.geojson`, `Carmen Cabrera.jpg`). GeoJSON, GPX and KML all work.
2. Optional: `raw/captions.csv` with columns `name,caption,lat,lon`.
3. `python prep.py` — trims 150 m off each route end, places photos (GPS, else route midpoint),
   strips all photo metadata and resizes. `raw/` is git-ignored and never published.
4. `quarto render`, then commit and push.

## Padlet links
Edit `_variables.yml` and re-render.

# GDSL Away Afternoon — 21 October 2026

Website for the Geographic Data Science Lab (University of Liverpool) Away Afternoon, held on Wednesday 21 October 2026, 13:00–15:00.

**Live site:** <https://pietrostefani.github.io/gdsl_oct2026/>

This year we replaced lightning talks with a map of how we move through Liverpool, short one-to-one chats and a four-table world café.

## What's on the site

| Page | File | Contents |
| --- | --- | --- |
| Programme | `index.qmd` | The two-hour run of show |
| Our Liverpool | `map.qmd` | Interactive map of lab members' routes through Liverpool, with a photo from each route |
| World café | `tables.qmd` | The four tables (Data, Place, Method, Problem), their prompts, QR codes and the two embedded Padlet boards |

## The map

Each person sent a route (GeoJSON, GPX or KML) and, optionally, one photo taken along it. `prep.py` turns these into the files the map reads:

- `data/routes.geojson`: one line per person, with route length in km
- `data/photos.geojson` and `data/photos/`: photo locations, resized photos and thumbnails

To protect privacy, `prep.py`:

- trims 150 m from both ends of every route, so start and end points (often home) are not shown;
- removes all metadata (EXIF, including GPS) from published photos;
- places each photo at its GPS location, moves it onto the route if it was taken more than 300 m away, and otherwise puts it at the route's midpoint;
- shows first names only (with an initial where two people share a first name).

Raw submissions live in `raw/`, which is git-ignored and never published.

The map uses [Leaflet](https://leafletjs.com/) (bundled in `assets/leaflet/`) on the Esri World Light Gray Canvas basemap, which needs no API key.

## Updating the site

Requirements: [Quarto](https://quarto.org/) and Python with `geopandas`, `pillow`, `pillow-heif` (for iPhone HEIC photos), `pyyaml`, `qrcode` and `jupyter`.

1. Put route files in `raw/routes/` and photos in `raw/photos/`, each named after the person (e.g. `Carmen Cabrera.geojson`, `Carmen Cabrera.jpg`).
2. Optional: add `raw/captions.csv` with the columns `name,caption,lat,lon`, to give photo captions or override photo locations.
3. Run `python prep.py`. It reports anyone with a route but no photo, and any files it couldn't read.
4. Run `quarto render`, which builds the site into `docs/`.
5. Commit and push. GitHub Pages serves `docs/` from the `main` branch.

The Padlet links are set in `_variables.yml` (`padlet_cafe` and `padlet_place`). Edit them there and re-render.

## Repository layout

```
_quarto.yml       site configuration (navbar, theme, output to docs/)
_variables.yml    Padlet links
styles.scss       colours (from the GDSL logo) and fonts (Candara, falling back to Cabin)
index.qmd         Programme page
map.qmd           Our Liverpool map
tables.qmd        World café page
prep.py           route and photo processing
assets/           logos and Leaflet
data/             processed routes and photos (published)
docs/             rendered site (published)
raw/              original submissions (not committed)
```

## Credits

Organised by Elisabetta Pietrostefani, Geographic Data Science Lab, University of Liverpool. Thanks to everyone who sent a route and to the table hosts.

Basemap tiles © Esri; map data © OpenStreetMap contributors.

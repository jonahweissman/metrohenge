# Metrohenge (Observable Framework + DuckDB)

DC Metro escalator data visualization and analysis tool using Observable Framework and DuckDB-WASM.

## Overview
- Static site built with Observable Framework
- Client-side DuckDB (duckdb-wasm) to query data in the browser
- Real OpenStreetMap data for DC Metro escalators
- Interactive SQL query interface

## Prerequisites
- Node 18+ recommended
- Python 3.7+ (for data loading)

## Quick Start

### 1. Install Dependencies
```bash
npm install
pip3 install -r requirements.txt
```

### 2. Load Fresh Data (Optional)
```bash
python3 data_loader.py --output src/data/dc_metro_escalators.csv
```

### 3. Development Server
```bash
npm run dev
```

### 4. Build for Production
```bash
npm run build
npm run preview
```

## Scripts

### Node.js
- `npm run dev` — local dev server (hot reload)
- `npm run build` — static build to `dist/`
- `npm run preview` — serve the static build

### Python Data Loader
- `python3 data_loader.py` — fetch latest escalator data from OSM
- `python3 data_loader.py --preview` — show preview of data without saving
- `python3 data_loader.py --bbox "south,west,north,east"` — custom bounding box

## Data

### Current Dataset
- **72 escalators** from DC Metro area
- Sourced from OpenStreetMap via Overpass API
- Includes outdoor escalators tagged with `highway=steps` and `conveying=*`
- Updated with latest OSM data when data loader is run

### Data Fields
- `id`: OSM way ID
- `name`: Escalator name (if available)
- `conveying`: Direction (yes, reversible, up, down, forward, backward)
- `incline`: Slope direction (up, down)
- `lat`, `lon`: Coordinates
- `level`: Floor levels (e.g., "-1;0")
- `tags`: All OSM tags
- `timestamp`, `user`: OSM metadata

### Sample Queries
```sql
-- Count by direction
SELECT conveying, count(*) FROM escalators GROUP BY 1 ORDER BY 2 DESC;

-- Find reversible escalators
SELECT id, name, lat, lon FROM escalators WHERE conveying = 'reversible';

-- Escalators by level
SELECT level, count(*) FROM escalators WHERE level IS NOT NULL GROUP BY 1;
```

## GitHub Pages Deployment

The GitHub Actions workflow is configured to automatically deploy to GitHub Pages:
- Builds on push to `main` branch
- Deploys to `gh-pages` using GitHub Pages artifact upload

## Architecture

- **Observable Framework**: Static site generator with reactive notebooks
- **DuckDB-WASM**: In-browser SQL engine for data analysis
- **Overpass API**: Real-time OpenStreetMap data source
- **Python Loader**: Custom data extraction and processing

## Development

### Adding New Queries
Edit `src/index.md` to add new SQL examples or modify the default query.

### Updating Data
Run `python3 data_loader.py` to fetch the latest escalator data from OpenStreetMap.

### Custom Queries
The Overpass query in `data_loader.py` can be modified to:
- Change geographic bounds
- Include different OSM features
- Add more tag filters

## License

Data sourced from OpenStreetMap contributors under ODbL license.


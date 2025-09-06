---
title: Metrohenge
---

# Metrohenge

This page loads DC Metro escalator data from OpenStreetMap into DuckDB (WebAssembly) and lets you run queries locally in your browser.

The dataset contains **72 escalators** from the DC Metro area, including outdoor escalators tagged with `highway=steps` and `conveying=*` in OpenStreetMap. Each escalator includes solar alignment calculations showing when the sun shines directly down the escalator at a 30° angle.

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";
import * as Inputs from "npm:@observablehq/inputs";
```

```js
// Initialize DuckDB client with normalized escalator and solar alignment data
const db = DuckDBClient.of({
  escalators: FileAttachment("data/dc_metro_escalators.csv"),
  solar_alignments: FileAttachment("data/dc_metro_solar_alignments.csv")
});
```

```js
// A query to show escalators with solar alignments using normalized tables
const defaultSQL = `
SELECT e.id, e.station_name, e.conveying, e.azimuth, 
       COUNT(sa.escalator_id) as alignment_count,
       MIN(sa.alignment_datetime) as first_alignment
FROM escalators e
INNER JOIN solar_alignments sa ON e.id = sa.escalator_id
GROUP BY e.id, e.station_name, e.conveying, e.azimuth
ORDER BY alignment_count DESC
LIMIT 10;`;
```

```js
// SQL input textarea using view() for reactivity
const sqlInput = view(Inputs.textarea({
  label: "SQL Query", 
  value: defaultSQL, 
  rows: 6,
  placeholder: "Enter your SQL query here..."
}));
```

```js
// Run query button using view() for reactivity  
const runButton = view(Inputs.button("Run Query"));
```

```js
// Execute query reactively - this cell re-runs when runButton is clicked
{
  runButton; // This creates the reactive dependency
  
  try {
    const sqlQuery = sqlInput || defaultSQL;
    const result = await db.sql([sqlQuery]);
    
    // Display results
    display(html`<h3>Query Results (${result.length} rows)</h3>`);
    display(Inputs.table(result, { rows: 15 }));
    
  } catch (error) {
    display(html`
      <div style="color: red; padding: 15px; border: 1px solid #ff6b6b; border-radius: 8px; margin-top: 20px; background-color: #ffe0e0;">
        <strong>❌ Query Error:</strong><br>
        <code>${error.message}</code>
      </div>
    `);
  }
}
```

## Sample Queries

Try these queries to explore the DC Metro escalator data:

**Basic Escalator Data:**
- **Count by direction**: `SELECT conveying, count(*) FROM escalators GROUP BY 1 ORDER BY 2 DESC;`
- **Escalators by station**: `SELECT station_name, count(*) as escalator_count FROM escalators WHERE station_name != '' GROUP BY 1 ORDER BY 2 DESC;`
- **Find reversible escalators**: `SELECT id, station_name, lat, lon FROM escalators WHERE conveying = 'reversible';`
- **Latest updates**: `SELECT id, station_name, user, timestamp FROM escalators ORDER BY timestamp DESC LIMIT 5;`

**Solar Alignment Queries (Using Joins):**
- **Escalators with most alignments**: `SELECT e.id, e.station_name, e.azimuth, COUNT(sa.escalator_id) as alignment_count FROM escalators e INNER JOIN solar_alignments sa ON e.id = sa.escalator_id GROUP BY e.id, e.station_name, e.azimuth ORDER BY alignment_count DESC;`
- **Summer alignments by station**: `SELECT e.station_name, COUNT(*) as summer_alignments FROM escalators e INNER JOIN solar_alignments sa ON e.id = sa.escalator_id WHERE sa.month IN (6, 7, 8) GROUP BY e.station_name ORDER BY summer_alignments DESC;`
- **Alignments by time of day**: `SELECT sa.hour, COUNT(*) as alignment_count FROM solar_alignments sa GROUP BY sa.hour ORDER BY sa.hour;`
- **Next upcoming alignment**: `SELECT e.station_name, e.id, sa.alignment_datetime FROM escalators e INNER JOIN solar_alignments sa ON e.id = sa.escalator_id WHERE sa.alignment_datetime > '2025-09-06' ORDER BY sa.alignment_datetime LIMIT 5;`

**Monthly Distribution:**
- **Alignments by month**: `SELECT sa.month, COUNT(*) as alignment_count FROM solar_alignments sa GROUP BY sa.month ORDER BY sa.month;`

The data is available as two normalized tables: `escalators` (basic escalator info) and `solar_alignments` (individual alignment events). Use JOINs to combine data from both tables. All queries run locally in your browser using DuckDB-WASM.


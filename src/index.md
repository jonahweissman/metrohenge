---
title: Metrohenge
---

# Metrohenge

**Metrohenge** tracks when the sun aligns perfectly with DC Metro escalators, shining directly down the escalator shaft. Like Stonehenge, these underground passages become solar calendars, marking specific moments throughout the year when celestial and urban geometry intersect.

Our dataset contains 46 escalators from 24 of the 47 underground Metro stations, with precise calculations of when the sun reaches a 30° elevation angle and aligns with each escalator's orientation.

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";
import * as Inputs from "npm:@observablehq/inputs";
import {html} from "npm:htl";
```

```js
// Initialize DuckDB client with normalized escalator and solar alignment data
const escalators = FileAttachment("data/dc_metro_escalators_escalators.parquet")
const solar_alignments = FileAttachment("data/dc_metro_escalators_solar_alignments.parquet")
const db = DuckDBClient.of();
```

## Upcoming Alignments

```js
// Get current datetime components
const now = new Date();
const currentYear = now.getFullYear();
const currentMonth = now.getMonth() + 1; // 1-12
const currentDay = now.getDate();
const currentHour = now.getHours();
const currentMinute = now.getMinutes();

// Get next upcoming alignment for each station
const upcoming = await db.sql([`
WITH base AS (
    SELECT 
        e.station_name,
        sa.escalator_id,
        make_timestamp(${currentYear}, sa.month, sa.day, sa.hour, sa.minute, 0) AS this_year_ts
    FROM read_parquet('${escalators.href}') e
    JOIN read_parquet('${solar_alignments.href}') sa ON e.id = sa.escalator_id
),
next_occurrences AS (
    SELECT
        station_name,
        CASE
            WHEN this_year_ts >= current_timestamp THEN this_year_ts
            ELSE this_year_ts + INTERVAL '1 year'
        END AS alignment_datetime
    FROM base
    ORDER BY alignment_datetime ASC
)
SELECT
    station_name,
    MIN(alignment_datetime) AS alignment_datetime
FROM next_occurrences
WHERE alignment_datetime >= current_timestamp
GROUP BY station_name
ORDER BY alignment_datetime ASC;

`]);

```

```js


display(Inputs.table(upcoming, {
  columns: [
    "station_name",
    "alignment_datetime"
  ],
  header: {
    station_name: "Station",
    alignment_datetime: "Next Alignment"
  },
  rows: 10
}));
```

## Recent Alignments

```js
// Get most recent alignment for each station
const recent = await db.sql([`
WITH base AS (
    SELECT 
        e.station_name,
        sa.escalator_id,
        make_timestamp(${currentYear}, sa.month, sa.day, sa.hour, sa.minute, 0) AS this_year_ts
    FROM read_parquet('${escalators.href}') e
    JOIN read_parquet('${solar_alignments.href}') sa ON e.id = sa.escalator_id
),
last_occurrences AS (
    SELECT
        station_name,
        CASE
            WHEN this_year_ts <= current_timestamp THEN this_year_ts
            ELSE this_year_ts - INTERVAL '1 year'
        END AS alignment_datetime
    FROM base
    ORDER BY alignment_datetime ASC
)
SELECT
    station_name,
    MAX(alignment_datetime) AS alignment_datetime
FROM last_occurrences
WHERE alignment_datetime <= current_timestamp
GROUP BY station_name
ORDER BY alignment_datetime DESC;
`]);
```

```js
display(Inputs.table(recent, {
  columns: [
    "station_name",
    "alignment_datetime"
  ],
  header: {
    station_name: "Station",
    alignment_datetime: "Recent Alignment"
  },
  rows: 10
}));
```

## Limitations

**Data Coverage**: Not every Metro station appears in our dataset. We only include escalators that are properly mapped in OpenStreetMap with directional metadata. Many underground stations may have escalators that aren't tagged in OSM, or use stairs/elevators instead.

**Solar Obstructions**: Our calculations assume clear line-of-sight from the sun to the escalator entrance. In reality, buildings, trees, and other structures may block sunlight, preventing the alignment effect even when astronomically predicted.

**Approximations**: We assume all escalators have a 30° incline angle and calculate alignments for when the sun reaches 30° elevation. Actual escalator angles and optimal viewing conditions may vary.

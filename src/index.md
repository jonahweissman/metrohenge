---
title: Metrohenge
---

# Metrohenge

This page loads DC Metro escalator data from OpenStreetMap into DuckDB (WebAssembly) and lets you run queries locally in your browser.

The dataset contains **72 escalators** from the DC Metro area, including outdoor escalators tagged with `highway=steps` and `conveying=*` in OpenStreetMap.

```js
import {DuckDBClient} from "npm:@observablehq/duckdb";
import * as Inputs from "npm:@observablehq/inputs";
```

```js
// Initialize DuckDB client with the escalator CSV data
const db = DuckDBClient.of({
  escalators: FileAttachment("data/dc_metro_escalators.csv")
});
```

```js
// A query to show escalator data
const defaultSQL = `SELECT id, name, conveying, incline, lat, lon, changeset FROM escalators LIMIT 10;`;
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

- **Count by direction**: `SELECT conveying, count(*) FROM escalators GROUP BY 1 ORDER BY 2 DESC;`
- **Escalators by incline**: `SELECT incline, count(*) FROM escalators WHERE incline IS NOT NULL GROUP BY 1;`
- **Find reversible escalators**: `SELECT id, name, lat, lon FROM escalators WHERE conveying = 'reversible';`
- **Latest updates**: `SELECT id, user, timestamp FROM escalators ORDER BY timestamp DESC LIMIT 5;`
- **Escalators with level info**: `SELECT id, conveying, level, incline FROM escalators WHERE level IS NOT NULL;`

The data is available as the `escalators` table. All queries run locally in your browser using DuckDB-WASM.


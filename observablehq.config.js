export default {
  title: "metrohenge",
  root: "src",
  // Default output is "dist"; leave as-is for now to follow Observable defaults.
  duckdb: {
      filesystem: {
        forceFullHTTPReads: true,
        reliableHeadRequests: false,
      },
      extensions: ["icu"]
  }
};


// ============================================================
// INST347 - Get Count Function
// GET /api/getCount  ->  { "count": 7, "apiVersion": "1" }
// ============================================================

const { app } = require("@azure/functions");
const { getContainer, COUNTER_ID } = require("../db");
const { API_VERSION } = require("../version");

app.http("getCount", {
  methods: ["GET"],
  authLevel: "anonymous",
  handler: async (request, context) => {
    try {
      const container = await getContainer();
      const { resource } = await container.item(COUNTER_ID, COUNTER_ID).read();

      // No document yet means nobody has clicked: the count is 0
      const count = resource ? resource.count : 0;

      return { status: 200, jsonBody: { count: count, apiVersion: API_VERSION } };
    } catch (error) {
      context.error("getCount failed: " + error.message);
      return { status: 500, jsonBody: { error: error.message } };
    }
  },
});

// ============================================================
// INST347 - Add One Function
// POST /api/addOne  ->  adds 1 to the count  ->  { "count": 8, "apiVersion": "1" }
// ============================================================

const { app } = require("@azure/functions");
const { getContainer, COUNTER_ID } = require("../db");
const { API_VERSION } = require("../version");

// Adds 1 inside the database ("incr"), so two clicks at the same moment
// both count. The first click ever creates the document instead.
async function addOne(container) {
  const item = container.item(COUNTER_ID, COUNTER_ID);
  try {
    const { resource } = await item.patch([{ op: "incr", path: "/count", value: 1 }]);
    return resource.count;
  } catch (error) {
    if (error.code !== 404) throw error;
  }

  try {
    const { resource } = await container.items.create({ id: COUNTER_ID, count: 1 });
    return resource.count;
  } catch (error) {
    // Someone else created it a moment ago: add our 1 to theirs
    if (error.code !== 409) throw error;
    const { resource } = await item.patch([{ op: "incr", path: "/count", value: 1 }]);
    return resource.count;
  }
}

app.http("addOne", {
  methods: ["POST"],
  authLevel: "anonymous",
  handler: async (request, context) => {
    try {
      const container = await getContainer();
      const count = await addOne(container);
      return { status: 200, jsonBody: { count: count, apiVersion: API_VERSION } };
    } catch (error) {
      context.error("addOne failed: " + error.message);
      return { status: 500, jsonBody: { error: error.message } };
    }
  },
});

// ============================================================
// INST347 - Shared Cosmos DB helper
// Both functions use this to reach the one counter document.
//
// The connection string comes from the CosmosDBConnection app setting
// (Function App > Settings > Environment variables). Never put it in code.
//
// The first call creates the database and container if they don't exist,
// so you don't have to make them by hand.
// ============================================================

const { CosmosClient } = require("@azure/cosmos");

const DATABASE_NAME = "counterdb";   // fixed names: keep as they are
const CONTAINER_NAME = "counts";
const COUNTER_ID = "clicks";          // the one document that holds the count

let containerPromise = null;

async function connect() {
  const connectionString = process.env.CosmosDBConnection;
  if (!connectionString) {
    throw new Error(
      "CosmosDBConnection app setting is not set. Add it in Function App > " +
      "Settings > Environment variables, then try again."
    );
  }

  const client = new CosmosClient(connectionString);
  const { database } = await client.databases.createIfNotExists({ id: DATABASE_NAME });
  const { container } = await database.containers.createIfNotExists({
    id: CONTAINER_NAME,
    partitionKey: { paths: ["/id"] },
  });
  return container;
}

// Returns the container, connecting once and reusing it after that.
// If connecting fails, the next call tries again.
function getContainer() {
  if (!containerPromise) {
    containerPromise = connect().catch((error) => {
      containerPromise = null;
      throw error;
    });
  }
  return containerPromise;
}

module.exports = { getContainer, COUNTER_ID };

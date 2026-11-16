# INST347 Team Counter (starter)

Version 1 of your team project: a website with one button. Each click adds 1 to a count stored in Cosmos DB. It's tiny on purpose. The point is the pipeline around it: push to GitHub and both apps deploy themselves.

Later you replace this code with your real project. The repo, resources, settings and pipeline stay.

## What's in the repo

```
frontend/            the website (Azure App Service)
  index.html         the page: shows the count, has the "Add 1" button
  server.js          tiny Node web server: sends index.html, and /config
  package.json       "npm start" runs server.js
api/                 the API (Azure Functions, Node.js)
  src/functions/
    getCount.js      GET  /api/getCount -> { count, apiVersion }
    addOne.js        POST /api/addOne   -> adds 1, returns { count, apiVersion }
  src/db.js          connects to Cosmos DB (creates the database and container if missing)
  src/version.js     API_VERSION: change it to see an API deploy go live
  host.json, package.json, package-lock.json
  local.settings.example.json   copy to local.settings.json to run locally (never commit it)
.gitignore           keeps node_modules and local.settings.json out of GitHub
```

## How the pieces connect

```
Browser --> Web App (frontend/) --/config--> API_BASE setting
Browser --> Function App (api/) --CosmosDBConnection setting--> Cosmos DB
```

| Where | Setting | Value |
|---|---|---|
| Web App | `API_BASE` (app setting) | Your Function App's address ending in `/api`, for example `https://YOUR-FUNCTION-APP.azurewebsites.net/api` |
| Function App | `CosmosDBConnection` (app setting) | The Cosmos DB account's primary connection string (a secret) |
| Function App | CORS | Your Web App's address, so the browser may call the API |

Settings live in Azure, not in the code. The connection string is a secret: never put it in a file you commit.

The database `counterdb`, the container `counts` (partition key `/id`) and the document `clicks` are created on the first request. Keep these names as they are.

## Run it on your laptop (optional)

You don't need this for class. GitHub Actions builds and deploys for you.

- Website: `cd frontend` and then `npm start`. It runs on http://localhost:8080. Set `API_BASE` first to point it at an API.
- API: needs Azure Functions Core Tools. Copy `local.settings.example.json` to `local.settings.json`, paste your connection string into it, then run `cd api`, `npm install` and `npm start`.

## Our team

<!-- Replace with your names, roles and links to your live site and API -->
- Team members:
- Azure host (owns the resource group):
- Live website:
- API:

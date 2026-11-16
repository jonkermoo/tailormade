// ============================================================
// INST347 - Tiny web server for the website
// App Service runs "npm start", which runs this file.
//   /        -> sends index.html
//   /config  -> tells the page where the API is (from the API_BASE app setting)
// No packages needed - it only uses what comes with Node.js.
// ============================================================

const http = require("http");
const fs = require("fs");
const path = require("path");

// App Service tells us which port to listen on through the PORT variable
const port = process.env.PORT || 8080;
const page = path.join(__dirname, "index.html");

http
  .createServer((request, response) => {
    const urlPath = request.url.split("?")[0];

    // The page asks here for the API address. It lives in an app setting,
    // not in the code, so each copy of the app can point at its own API.
    if (urlPath === "/config") {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ apiBase: process.env.API_BASE || "" }));
      return;
    }

    if (urlPath === "/" || urlPath === "/index.html") {
      fs.readFile(page, (error, contents) => {
        if (error) {
          response.writeHead(500, { "Content-Type": "text/plain" });
          response.end("index.html not found next to server.js");
          return;
        }
        response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        response.end(contents);
      });
      return;
    }

    // Anything else really doesn't exist. A clear 404 beats sending the
    // page back for every address, which hides mistakes.
    response.writeHead(404, { "Content-Type": "text/plain" });
    response.end("Not found: " + urlPath);
  })
  .listen(port, () => console.log("Website running on port " + port));

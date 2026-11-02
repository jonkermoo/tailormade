"""User-facing HTTP API, deployed as the Static Web Apps managed API.

Endpoints for jobs, saved filters, the application tracker and resume
tailoring will live here. For now there is only a health check.
"""
import json
from datetime import datetime, timezone

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    body = {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
    return func.HttpResponse(json.dumps(body), mimetype="application/json")

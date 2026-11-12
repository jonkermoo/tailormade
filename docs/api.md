# TailorMade API design

Owner: Lina Romero (backend API)

This doc lists every endpoint the frontend talks to, what it takes, and what it sends back. The goal is for the frontend and backend to agree on the shapes **before** we build them, so Ayomide can build screens without waiting on finished code.

Status key: ✅ built · 🛠 planned

## Basics

- **Base URL:** `/api` (locally `http://localhost:7071/api`; the Vite dev server forwards `/api` there, so the frontend can just call `/api/...`)
- **Format:** JSON in, JSON out
- **Who's calling:** Static Web Apps handles login. Every request after sign-in carries the user in the `x-ms-client-principal` header, and the API uses that to find the row in `users`. Users only ever see their own filters, applications and resumes.
- **Field names** match the columns in `db/schema.sql` (snake_case).
- **Errors** always look like this, with a matching status code (400, 401, 404, 500):
  ```json
  { "error": "Job 42 not found" }
  ```

## Endpoints at a glance

| Method | Path | What it does | Sprint | Status |
|---|---|---|---|---|
| GET | `/api/health` | Check the API is up | 0 | ✅ |
| GET | `/api/jobs` | Job feed, with search and filters | 0–1 | ✅ (sample data) |
| GET | `/api/jobs/{id}` | One job, with full description | 1 | 🛠 |
| GET | `/api/filters` | List my saved filters | 2 | 🛠 |
| POST | `/api/filters` | Save a new filter | 2 | 🛠 |
| GET | `/api/applications` | My tracker board | 2 | 🛠 |
| POST | `/api/applications` | Add a job to my board | 2 | 🛠 |
| PATCH | `/api/applications/{id}` | Move a card / edit notes | 2 | 🛠 |
| GET | `/api/profile` | My resume profile | 3 | 🛠 |
| PUT | `/api/profile` | Save my resume profile | 3 | 🛠 |
| POST | `/api/tailor/{jobId}` | Tailor my resume to a job | 3 | 🛠 |

## Jobs

### `GET /api/jobs` ✅

The main feed. Newest first.

| Query param | Example | Meaning | Status |
|---|---|---|---|
| `q` | `engineer` | Title contains this (case-insensitive) | ✅ |
| `filterId` | `3` | Apply one of my saved filters | 🛠 |
| `location` | `Seattle` | Location contains this | 🛠 |
| `remote` | `true` | Remote jobs only | 🛠 |

Response:
```json
{
  "count": 1,
  "jobs": [
    {
      "id": 3,
      "company": "GitLab",
      "title": "Backend Engineer (Python)",
      "location": "Remote, US",
      "is_remote": true,
      "posted_at": "2026-10-29T17:15:00Z",
      "url": "https://about.gitlab.com/jobs"
    }
  ]
}
```

`url` comes from `job_sources` (the first place we found the job). Right now the data comes from `api/sample_jobs.json`. Once Ebulo's seed data and filter query are in, it switches to Azure SQL with the same response shape, so the frontend doesn't change.

### `GET /api/jobs/{id}` 🛠

Same fields as above, plus `description` (the full posting text the tailor needs).

## Saved filters

### `GET /api/filters` 🛠

```json
{
  "filters": [
    {
      "id": 1,
      "name": "Junior backend",
      "keywords": "backend,python",
      "locations": "Seattle,Remote",
      "remote_only": false,
      "min_score": 70,
      "alerts_enabled": true
    }
  ]
}
```

### `POST /api/filters` 🛠

Body: the same fields minus `id`. Only `name` is required; the rest use the database defaults (`min_score` 70, alerts on). Returns the new filter with its `id` and a `201`.

## Application tracker

Board columns follow the `status` values in the schema: `saved` → `applied` → `interview` → `offer` (or `rejected`).

### `GET /api/applications` 🛠

```json
{
  "applications": [
    {
      "id": 12,
      "status": "applied",
      "notes": "Referred by a friend",
      "applied_at": "2026-11-20T15:00:00Z",
      "updated_at": "2026-11-20T15:00:00Z",
      "resume_version_id": 5,
      "job": { "id": 3, "company": "GitLab", "title": "Backend Engineer (Python)" }
    }
  ]
}
```

### `POST /api/applications` 🛠

Body: `{ "job_id": 3 }`. It starts in `saved`. Adding the same job twice returns `409` (the schema has a unique rule on user + job).

### `PATCH /api/applications/{id}` 🛠

Send only what changed:
```json
{ "status": "interview", "notes": "Phone screen Friday" }
```
Moving to `applied` fills in `applied_at` automatically. Returns the updated application.

## Profile and resume tailor

### `GET /api/profile` · `PUT /api/profile` 🛠

The user's resume info, stored once in `users.profile_json`: contact info, education, experience (each with bullets) and skills. The tailor only ever rewords what's in here.

### `POST /api/tailor/{jobId}` 🛠

Sends my profile and the job description to Azure OpenAI (gpt-4o-mini) using Joshua's prompt, saves the PDF to Blob Storage, and records a row in `resume_versions`.

Response:
```json
{
  "resume_version_id": 5,
  "match_score": 78,
  "missing_skills": ["Kubernetes", "Go"],
  "bullets": [
    "Built a REST API in Python serving job listings to a React dashboard"
  ],
  "pdf_url": "https://<storage>.blob.core.windows.net/resumes/..."
}
```

**Guardrail:** the tailor can only reword facts from the profile. It never invents jobs, degrees or skills. Anything the job wants that the profile doesn't have goes in `missing_skills` instead.

If the model sends back broken JSON, the API retries once, then returns a `502` with a clear error instead of crashing.

## What I need from teammates

- **Ebulo:** seed data and the saved-filter query, so `/api/jobs` can move to SQL
- **Joshua:** the tailoring prompt
- **Johnny:** the Azure SQL connection details and the Azure OpenAI deployment
- **Ayomide:** tell me if any of these shapes don't work for a screen, before I build it
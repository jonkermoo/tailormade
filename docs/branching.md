# Branching and workflow

## Branches

- `main` always deploys. It is protected: pull request required, at least one approving review, no force pushes.
- Work happens on short-lived branches cut from `main`:
  - `feature/<name>-<thing>`, e.g. `feature/ayomide-tracker-board`
  - `fix/<name>-<thing>`, e.g. `fix/lina-filter-query`
- Delete the branch after it merges.

## Day to day

```bash
git checkout main
git pull
git checkout -b feature/<name>-<thing>
# work, commit small and often
git push -u origin feature/<name>-<thing>
# open a pull request on GitHub and ask a teammate to review
```

## Pull requests

- Fill in the PR template and link the issue it closes (`Closes #12`).
- CI must pass before merging.
- Squash-merge to keep `main` history readable.

## Tracking progress

- Every task is a GitHub issue, assigned to one person, on the project board (Backlog, In progress, In review, Done).
- Each sprint is a milestone with a due date.

| Milestone | Dates | Goal |
|---|---|---|
| Sprint 0 | Nov 2 – Nov 8 | Repo, Azure resources, local environments |
| Sprint 1 | Nov 9 – Nov 15 | Crawler to queue to database; React shell with sign-in |
| Sprint 2 | Nov 16 – Nov 22 | Filters and scoring, tracker, live alerts |
| Sprint 3 | Nov 23 – Dec 6 | Resume tailoring and PDF export |
| Sprint 4 | Dec 7 – Dec 13 | Polish, deployed demo, presentation |

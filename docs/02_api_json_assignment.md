# REST APIs & JSON — Assignment writeup

## What is an API?

An API (Application Programming Interface) is a defined contract that lets two pieces of software talk to each other — one side asks for something, the other side responds, without either needing to know the other's internal implementation.

## HTTP methods used here

| Method | Purpose | Used in this assignment? |
|---|---|---|
| GET | Retrieve a resource without changing it | Yes — fetching repository search results |
| POST | Create a new resource / submit data | No |

## The API called

**Endpoint**: `GET https://api.github.com/search/repositories`
**Query parameters used**:
- `q=topic:fintech language:python` — search filter
- `sort=stars&order=desc` — ranking
- `per_page=10` — pagination size

**Authentication**: none required for this endpoint (public, unauthenticated requests are rate-limited to a modest hourly quota — a good illustration of why production integrations use API keys/tokens for higher limits).

## JSON response shape (inspected)

The top-level JSON object has:
```json
{
  "total_count": 3617,
  "incomplete_results": false,
  "items": [ { "name": "...", "owner": {...}, "stargazers_count": 48069, ... }, ... ]
}
```
Each item in `items` is a repository object with 70+ fields; the assignment script (`fetch_api_data.py`) selects the eight fields relevant for analysis (`repo_name`, `owner`, `stars`, `forks`, `language`, `open_issues`, `url`, `description`) and discards the rest.

## Output produced

Running `python3 api_assignment/fetch_api_data.py` produces:
- `api_response_raw.json` — the full raw API response, saved verbatim for auditability
- `github_fintech_repos.csv` — the flattened, analysis-ready CSV

This mirrors exactly what the Sprint 1 ETL pipeline does at a larger scale: pull semi-structured source data (JSON here, Excel there), select and clean the fields that matter, and land a clean tabular file for downstream use.

## Postman / Bruno note

The same request can be replicated in Postman or Bruun by creating a `GET` request to the endpoint above with the three query parameters set in the **Params** tab, and inspecting the response body in the **Body → Pretty (JSON)** view — useful for exploring an API's shape before writing code against it.

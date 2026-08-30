# Basic Software Development Concepts

## Frontend vs backend

- **Frontend** — the part of an application the user sees and interacts with (buttons, forms, dashboards). Built with HTML/CSS/JavaScript or frameworks like React.
- **Backend** — the server-side logic that processes requests, applies business rules, and talks to the database. Built with languages like Python, Java, Node.js, etc.

## Client–server architecture

The **client** (e.g. a browser or mobile app) sends requests to a **server**, which processes them and sends back a response. Neither needs to know the other's internal implementation — they only need to agree on the interface (the API).

## REST APIs

A REST API exposes resources (e.g. `/users`, `/orders`) over HTTP, using standard verbs (GET, POST, PUT, DELETE) to read, create, update, or delete them. See `docs/02_api_json_assignment.md` for a hands-on example.

## Authentication

The process of verifying who is making a request — common approaches include username/password login, API keys, and token-based auth (e.g. JWT, OAuth). Authorization (what an authenticated user is *allowed* to do) is a separate, related concept.

## Databases

Structured storage for an application's data. This internship's Sprint 1 project (`nifty100-etl/`) is a complete worked example: a SQLite database (`nifty100.db`) with 10+ related tables, primary/foreign keys, and constraints — the same relational concepts that power production databases like PostgreSQL or MySQL, just at a smaller scale.

## Data pipelines

An automated sequence of steps that moves data from a raw source to a usable destination — typically **Extract** (pull from source), **Transform** (clean/normalize/validate), **Load** (write to a database). Sprint 1's `loader.py` + `normaliser.py` + `validator.py` is exactly this ETL pattern, applied to 12 Excel source files landing in an 11-table SQLite schema.

## Logging & error handling

- **Logging** — recording what a system did (and when) for debugging and auditing. `output/load_audit.csv` in the Sprint 1 project is a form of structured logging: it records, per table, how many rows were read, loaded, and rejected.
- **Error handling** — code that anticipates things going wrong (bad input, network failures, missing files) and responds gracefully instead of crashing. `loader.py`'s rejection logic (dropping rows with bad years or orphan foreign keys, rather than failing the whole load) and `fetch_api_data.py`'s retry-with-backoff logic are both examples.

## Basic SDLC (Software Development Lifecycle)

A typical cycle: **Requirements → Design → Development → Testing → Deployment → Maintenance**, often run iteratively (as in Agile/Scrum sprints, like the Sprint 1 board this internship uses — Day 01–07, story points, a sprint goal, and a retrospective).

## Data flow diagram

See `diagrams/data_flow_architecture.svg` (also rendered inline in this conversation) for a simple diagram of how data flows from a user action in a web app, through a backend API, into a database, through an ETL pipeline, and finally into an analytics dashboard.

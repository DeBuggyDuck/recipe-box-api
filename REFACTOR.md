# Refactor Plan

## 1. Responsibility Inventory (count: 9)
1. Environment & secrets configuration: Loading variables from `.env` into runtime scope.
2. Database connection lifecycle: Managing SQLite connection opening, row factory mapping, and teardown.
3. Data serialization: Converting raw database cursor rows into clean API JSON dictionaries.
4. Authentication middleware: Parsing Authorization bearer headers, verifying JWT signatures, and attaching claims to request context.
5. Identity & user routes: Handling incoming registration and login payloads, password hashing, and token issuance.
6. Domain resource routes: Defining URL routing and HTTP methods for recipe collection and items.
7. Direct SQL execution: Writing raw queries, executing database transactions, and enforcing database-level integrity.
8. Authorization policy checks: Inspecting user identity against resource ownership and applying admin role overrides.
9. Server instantiation & entry point: Initializing the Flask application instance and executing the development server.

## 2. Target Architecture Layout
- Top-level app package (`app/`): Holds package initialization, application factory (`create_app`), and global extension wiring.
- Routes / presentation layer (`app/api/`): Blueprint modules defining HTTP endpoints, parameter extraction, and status code responses.
- Services & business logic (`app/services/`): Pure business logic, authorization rules, hashing, and token handling decoupled from Flask requests.
- Data access & persistence (`app/db/`): Database connection helpers, connection pooling/context lifecycle, and query execution.
- Shared core utilities (`app/core/`): Cross-cutting helpers including `@token_required` decorators, standard error handlers, and serializers.

## 3. Acceptance Test Matrix (count: 22)
1. `POST /register` — Valid payload with unique username, email, and password → 201 Created, returns user dict without password hash.
2. `POST /register` — Missing required username, email, or password field → 400 Bad Request, returns validation error message.
3. `POST /register` — Duplicate username or email collision → 409 Conflict, returns duplicate user message.
4. `POST /login` — Valid username and password → 200 OK, returns signed JWT `{"token": "<jwt>"}`.
5. `POST /login` — Missing username or password in payload → 400 Bad Request, returns missing credentials message.
6. `POST /login` — Unregistered user or invalid password → 401 Unauthorized, returns invalid credentials message.
7. `GET /` — Root health check request → 200 OK, returns API status and link index.
8. `GET /recipes` — Anonymous request (no token) → 200 OK, returns JSON array of public recipes only.
9. `GET /recipes` — Authenticated request with valid token → 200 OK, returns JSON array of public recipes plus private recipes owned by caller.
10. `GET /recipes/<id>` — Anonymous request for public recipe → 200 OK, returns recipe details.
11. `GET /recipes/<id>` — Authenticated owner request for private recipe → 200 OK, returns recipe details.
12. `GET /recipes/<id>` — Anonymous request for private recipe → 401 Unauthorized, returns authentication required error.
13. `GET /recipes/<id>` — Authenticated non-owner request for private recipe → 403 Forbidden, returns permission denied error.
14. `GET /recipes/<id>` — Non-existent recipe ID → 404 Not Found, returns resource missing error.
15. `POST /recipes` — Valid token and complete recipe payload → 201 Created, returns created recipe stamped with user ID.
16. `POST /recipes` — Missing or invalid Bearer token → 401 Unauthorized, returns missing or invalid token error.
17. `POST /recipes` — Valid token but missing required fields (title/ingredients) → 400 Bad Request, returns validation failure.
18. `PATCH /recipes/<id>` — Valid token from recipe owner or admin → 200 OK, returns updated recipe record.
19. `PATCH /recipes/<id>` — Valid token from non-owner standard user → 403 Forbidden, returns unauthorized modification error.
20. `PATCH /recipes/<id>` — Missing or invalid Bearer token → 401 Unauthorized, returns missing or invalid token error.
21. `PATCH /recipes/<id>` — Target recipe ID does not exist → 404 Not Found, returns resource missing error.
22. `DELETE /recipes/<id>` — Valid token from owner or admin → 204 No Content, removes recipe.

## 4. Summary Counts
- Distinct responsibilities in app.py: 9
- Acceptance-list items (scenarios): 22
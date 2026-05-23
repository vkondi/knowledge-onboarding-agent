# REST API Design

REST (Representational State Transfer) is an architectural style for designing networked APIs over HTTP.

## Core Principles

1. **Uniform interface** — consistent resource URLs and HTTP methods across the API.
2. **Statelessness** — every request is self-contained; the server holds no client session state.
3. **Client–server separation** — the UI and data storage are decoupled.
4. **Cacheability** — responses must declare whether they can be cached.
5. **Layered system** — clients don't need to know if they're talking to a load balancer, proxy, or the actual server.

## HTTP Methods

| Method | Use | Idempotent? | Safe? |
|---|---|---|---|
| GET | Read a resource | ✓ | ✓ |
| POST | Create a resource | ✗ | ✗ |
| PUT | Replace a resource completely | ✓ | ✗ |
| PATCH | Partially update a resource | ✗ | ✗ |
| DELETE | Remove a resource | ✓ | ✗ |

**Idempotent**: calling the operation multiple times has the same effect as calling it once.
**Safe**: the operation does not modify server state.

## URL Design

Resources are nouns, not verbs. Use plural for collections.

```
GET    /users              # list all users
POST   /users              # create a user
GET    /users/42           # get user 42
PUT    /users/42           # replace user 42
PATCH  /users/42           # partially update user 42
DELETE /users/42           # delete user 42

GET    /users/42/orders    # orders belonging to user 42
GET    /orders/7           # order 7 directly
```

Avoid verb-based URLs: ~~`/getUser`~~, ~~`/createOrder`~~, ~~`/deleteUser?id=42`~~

## HTTP Status Codes

| Code | Meaning | When to use |
|---|---|---|
| 200 OK | Success | GET, PUT, PATCH responses |
| 201 Created | Resource created | POST responses; include `Location` header |
| 204 No Content | Success, no body | DELETE responses |
| 400 Bad Request | Invalid input | Validation failures |
| 401 Unauthorized | Not authenticated | Missing or invalid token |
| 403 Forbidden | Authenticated but not authorised | Accessing another user's data |
| 404 Not Found | Resource doesn't exist | |
| 409 Conflict | State conflict | Duplicate creation, optimistic locking |
| 422 Unprocessable Entity | Semantically invalid | Business rule violations |
| 500 Internal Server Error | Unexpected server error | Never expose stack traces |

## Request and Response Format

Use JSON. Set `Content-Type: application/json`.

**Request body (POST /users):**
```json
{
  "email": "alice@example.com",
  "name": "Alice",
  "role": "editor"
}
```

**Response body (201 Created):**
```json
{
  "id": "usr_abc123",
  "email": "alice@example.com",
  "name": "Alice",
  "role": "editor",
  "created_at": "2026-01-15T09:30:00Z"
}
```

**Error response:**
```json
{
  "error": "validation_failed",
  "message": "email is already registered",
  "field": "email"
}
```

## Versioning

APIs change over time. Version them to avoid breaking existing clients.

```
# URI versioning (most common)
/v1/users
/v2/users

# Header versioning (cleaner URLs, harder to test in browser)
Accept: application/vnd.myapi.v2+json
```

Rules:
- Never make breaking changes within a version.
- Support the previous version for at least 12 months after deprecation.
- Communicate breaking changes in changelogs and via `Sunset` response headers.

## Pagination

Never return unbounded collections. Use cursor-based or offset pagination.

**Offset pagination** (simpler, but inconsistent under concurrent writes):
```
GET /orders?page=2&per_page=25
```
```json
{
  "data": [...],
  "pagination": {
    "total": 1240,
    "page": 2,
    "per_page": 25,
    "total_pages": 50
  }
}
```

**Cursor pagination** (consistent, works well with real-time data):
```
GET /orders?after=cursor_xyz&limit=25
```
```json
{
  "data": [...],
  "next_cursor": "cursor_abc",
  "has_more": true
}
```

## Authentication

- **Bearer token (JWT)**: include in `Authorization: Bearer <token>` header. Don't put tokens in URLs.
- **API keys**: for server-to-server calls; rotate regularly and store in secrets manager, never in code.
- **OAuth2**: for user-delegated access (login with GitHub/Google).

## Rate Limiting

Protect your API from abuse by limiting requests per client.

Return `429 Too Many Requests` with a `Retry-After` header:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1716300000
Retry-After: 60
```

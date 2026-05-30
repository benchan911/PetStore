# CarePets

A pet care marketplace connecting pet owners with caretakers. Owners post jobs; caretakers apply; owners confirm.

## Architecture

```
frontend (Next.js 15, port 3000)
    │
    └─▶ gateway (nginx, port 8080)
              ├─▶ auth_service    (Flask, port 5001)  /api/auth/*
              ├─▶ users_service   (Flask, port 5002)  /api/users/*
              ├─▶ pets_service    (Flask, port 5003)  /api/pets/*
              └─▶ bookings_service(Flask, port 5004)  /api/bookings/*

Data layer: Supabase (hosted Postgres + Auth)
```

## Prerequisites

- Docker Desktop (for backend)
- Node.js 20 (for frontend)
- Python 3.11 (for running backend tests locally)
- A [Supabase](https://supabase.com) project

## Supabase Setup

1. Create a new Supabase project.
2. In the **SQL Editor**, run `backend/sql/schema.sql` to create all tables.
3. Run `backend/sql/seed.sql` to populate sample data.
   - Seed creates 7 users (3 owners, 4 caretakers) with password `Password123!`
4. Copy your project credentials from **Project Settings → API**.

## Backend

### Configure

```bash
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Project Settings → API → anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API → service_role key |
| `JWT_SECRET` | Project Settings → API → JWT Settings → JWT Secret |
| `SMTP_HOST` | `smtp.gmail.com` for Gmail / Google Workspace |
| `SMTP_PORT` | `587` (STARTTLS) |
| `SMTP_USERNAME` | Your full email address (e.g. `solaiym.2022@scis.smu.edu.sg`) |
| `SMTP_PASSWORD` | Google App Password — generate at **myaccount.google.com → Security → 2-Step Verification → App passwords** (requires 2FA to be enabled first) |

### Run

```bash
cd backend
docker compose up --build
```

This starts the nginx gateway and all four Flask services. The gateway is available at `http://localhost:8080`.

### Test

```bash
# Test a single service
pip install -r backend/services/auth/requirements.txt pytest
cd backend/services/auth
pytest tests/ -v

# Or all services
for svc in auth users pets bookings; do
  pip install -r backend/services/$svc/requirements.txt pytest
  (cd backend/services/$svc && pytest tests/ -v)
done
```

## Frontend

### Configure

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8080/api
```

### Run

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Test

```bash
cd frontend
npm test -- --watchAll=false
```

### Build

```bash
cd frontend
npm run build
```

## Project Layout

```
PetStore/
├── backend/
│   ├── docker-compose.yaml
│   ├── .env.example
│   ├── gateway/
│   │   └── nginx.conf
│   ├── shared/
│   │   ├── jwt_middleware.py   # @jwt_required / @role_required decorators
│   │   ├── email_service.py    # SMTP helpers
│   │   └── supabase_client.py
│   ├── services/
│   │   ├── auth/               # signup, login, logout, /me
│   │   ├── users/              # profile CRUD, caretaker listing
│   │   ├── pets/               # pet CRUD (owner-only)
│   │   └── bookings/           # booking CRUD, apply, confirm
│   └── sql/
│       ├── schema.sql
│       └── seed.sql
└── frontend/
    ├── app/                    # Next.js App Router pages
    ├── components/             # Shared UI components
    ├── lib/
    │   ├── api.js              # Fetch wrapper with JWT injection
    │   └── auth.js             # AuthContext + useAuth hook
    └── __tests__/              # Jest + Testing Library tests
```

## Notes

- Email notifications (applicant confirmed/rejected) are sent synchronously in the request cycle. For production, move to a background queue.
- JWT verification calls the Supabase `/auth/v1/user` endpoint, which validates RS256-signed tokens server-side.
- Caretaker role is stored in Supabase `user_metadata` during signup and embedded in issued JWTs.

---

## Security Considerations

### Password Hashing

Passwords are never stored or handled in plaintext by any CarePets service. The `auth` service passes credentials directly to **Supabase Auth**, which stores passwords hashed with **bcrypt** (cost factor 10). The plain-text password only travels over HTTPS between the client and the auth service, and is never logged or persisted by application code.

### JWT Authentication (RS256)

Supabase issues **RS256-signed JWTs** upon successful login. The private signing key never leaves Supabase's infrastructure. Every protected endpoint runs the `@jwt_required` decorator from `backend/shared/jwt_middleware.py`, which validates the token by calling `GET /auth/v1/user` on the Supabase API — meaning verification always goes back to the issuer rather than relying on a locally-stored secret that could be compromised.

```
Request → Bearer <token>
  └─▶ jwt_middleware.verify_jwt()
        └─▶ POST /auth/v1/user (Supabase)
              ├── valid  → g.user_id, g.role set → handler called
              └── invalid → 401 returned immediately
```

### Role-Based Access Control (RBAC)

The user's role (`owner` or `caretaker`) is embedded in `user_metadata` at signup and propagated through the JWT. The `@role_required('owner')` decorator, stacked on top of `@jwt_required`, gates endpoints so that, for example, a caretaker cannot create a booking or confirm an application. The role is read from the verified JWT payload — it cannot be self-assigned per request.

### Row Level Security (RLS)

Supabase's Postgres RLS policies form a second enforcement layer independent of application code. Key policies:

| Table | Policy |
|---|---|
| `profiles` | Users can only read/update their own row; public read allowed for caretaker browsing |
| `pets` | Owners can only SELECT/INSERT/UPDATE/DELETE their own pets (`auth.uid() = owner_id`) |
| `bookings` | Owners manage their own bookings; caretakers can only SELECT rows with `status = 'open'` |
| `applications` | Caretakers manage their own applications; owners can view applications on their bookings via a subquery |

Even if application-level auth were bypassed, RLS would still prevent cross-user data access. The backend services use the `SERVICE_ROLE_KEY`, which bypasses RLS so services can operate freely, but this key is never exposed to the browser.

### Input Validation

Validation is applied at two boundaries:

- **Frontend** — Zod schemas (e.g., `signup/page.js`) validate field types and constraints before any request leaves the browser.
- **Backend** — Each Flask endpoint checks required fields explicitly (e.g., `if not all([pet_id, start_date, end_date, description])`) and the database enforces `CHECK` constraints on enum-like columns (`role IN ('owner','caretaker')`, `status IN ('open','confirmed','cancelled')`).

### CORS

nginx adds `Access-Control-Allow-Origin: http://localhost:3000` on every response. Pre-flight `OPTIONS` requests return 204 immediately. In production this origin should be updated to the deployed frontend domain.

### Ownership Verification

Application logic verifies ownership before mutations even when RLS is active, providing defence-in-depth:

- Creating a booking: pet existence **and** `owner_id = current user` are both verified before insert.
- Confirming a booking: `bookings.owner_id = current user` is checked before any status updates are made.
- Updating a profile: `user_id` in the URL is compared against `g.user_id` from the JWT.

---

## CIA Triad Analysis

### Confidentiality

| Control | How it is implemented |
|---|---|
| Password secrecy | bcrypt hashing in Supabase Auth; plain-text never stored |
| Data access control | RLS policies restrict rows to their owners |
| Token secrecy | RS256 private key stays in Supabase; service role key never sent to browser |
| Role separation | Caretakers cannot read owner-only data; owners cannot see other owners' pets |
| Transport | All browser → gateway traffic should run over HTTPS in production; nginx forwards `X-Forwarded-Proto` |

### Integrity

| Control | How it is implemented |
|---|---|
| Schema constraints | `CHECK` constraints enforce valid `role` and `status` values at the DB level |
| Uniqueness | `UNIQUE(booking_id, caretaker_id)` prevents a caretaker submitting multiple applications to the same booking |
| Ownership checks | Mutations verify the requesting user owns the resource before proceeding |
| Timestamp accuracy | `updated_at` triggers fire on every `UPDATE`, maintaining an accurate audit trail |
| Atomic status transitions | Confirming a booking updates the booking status and all sibling applications in a single service operation, keeping state consistent |

### Availability

**Current architecture strengths:**

- **Service isolation** — each microservice is an independent container. A crash in the `bookings` service does not affect `auth`, `users`, or `pets`. nginx returns `502` only for routes to the failed service.
- **Managed data layer** — Supabase is a hosted, HA Postgres service with automatic failover and backups; the application does not need to manage database availability itself.
- **Stateless services** — JWT verification is stateless (no session store), so any replica of a service can handle any request.

**How nginx load balancing would improve availability (conceptual):**

nginx's `upstream` blocks already name each backend service. Adding multiple server entries and a balancing policy is the only change required:

```nginx
upstream bookings_service {
    least_conn;                  # route to the instance with fewest active connections
    server bookings_1:5004;
    server bookings_2:5004;
    server bookings_3:5004;
}
```

With `docker compose --scale bookings=3`, nginx would distribute traffic across three replicas using the `least_conn` algorithm and automatically stop routing to any instance that stops responding. This eliminates the bookings service as a single point of failure. The same pattern applies to all four Flask services.

For production, adding `keepalive 32;` to the upstream block reduces connection overhead, and `proxy_next_upstream error timeout` instructs nginx to retry failed requests on the next healthy upstream.

---

## Microservices Architecture Diagram

```mermaid
flowchart TD
    Browser["fa:fa-globe Browser\nNext.js 15 · :3000"]

    subgraph docker ["Docker Compose Network (carepets)"]
        GW["nginx Gateway\n:8080"]

        subgraph services ["Flask Microservices"]
            Auth["Auth Service\n:5001\n/auth/*"]
            Users["Users Service\n:5002\n/users/*"]
            Pets["Pets Service\n:5003\n/pets/*"]
            Bookings["Bookings Service\n:5004\n/bookings/*"]
        end

        SharedLib[["Shared Library\njwt_middleware.py\nemail_service.py"]]
    end

    Supabase[("Supabase\nPostgres + Auth\n+ RLS")]
    SMTP["SMTP\nEmail (Gmail)"]

    Browser -- "HTTP /api/*" --> GW
    GW -- "/auth/*" --> Auth
    GW -- "/users/*" --> Users
    GW -- "/pets/*" --> Pets
    GW -- "/bookings/*" --> Bookings

    Auth -. "uses" .-> SharedLib
    Users -. "uses" .-> SharedLib
    Pets -. "uses" .-> SharedLib
    Bookings -. "uses" .-> SharedLib

    Auth -- "sign up / sign in\nDB queries" --> Supabase
    Users -- "profile CRUD" --> Supabase
    Pets -- "pet CRUD" --> Supabase
    Bookings -- "booking + application CRUD" --> Supabase
    SharedLib -- "verify token\nGET /auth/v1/user" --> Supabase

    Bookings -- "confirmed / rejected\nnotifications" --> SMTP
```

**Request flow — creating a booking:**

1. Browser sends `POST /api/bookings` with `Authorization: Bearer <JWT>`.
2. nginx matches `/api/bookings` and rewrites + proxies to `bookings:5004/bookings`.
3. `@jwt_required` calls Supabase `/auth/v1/user` to validate the token and populate `g.user_id`.
4. `@role_required('owner')` checks `g.role == 'owner'`.
5. Handler verifies the referenced pet belongs to `g.user_id`, then inserts the booking row.
6. Supabase RLS policies are enforced at the database level as a second check.

---

## C4 Diagram

### Level 1 — System Context

```mermaid
C4Context
    title CarePets — System Context

    Person(owner, "Pet Owner", "Posts pet care jobs and confirms caretakers")
    Person(caretaker, "Caretaker", "Browses open jobs and submits applications")

    System(carepets, "CarePets", "Pet care marketplace web application")

    System_Ext(supabase, "Supabase", "Managed Postgres database with built-in Auth, JWT issuance, and Row Level Security")
    System_Ext(smtp, "SMTP / Gmail", "Sends transactional emails to notify caretakers of application outcomes")

    Rel(owner, carepets, "Signs up, posts jobs, confirms caretakers", "HTTPS")
    Rel(caretaker, carepets, "Signs up, browses jobs, applies", "HTTPS")
    Rel(carepets, supabase, "Persists all data and authenticates users", "HTTPS / REST")
    Rel(carepets, smtp, "Sends booking outcome notifications", "SMTP / STARTTLS")
```

### Level 2 — Container Diagram

```mermaid
C4Container
    title CarePets — Container Diagram

    Person(owner, "Pet Owner")
    Person(caretaker, "Caretaker")

    Container_Boundary(fe, "Frontend") {
        Container(frontend, "Next.js App", "Next.js 15 / React", "Renders pages, manages JWT in localStorage, calls backend API via fetch wrapper")
    }

    Container_Boundary(be, "Backend — Docker Compose") {
        Container(gateway, "nginx Gateway", "nginx 1.25", "Single ingress. Routes /api/* to services, terminates CORS pre-flight, forwards real IP headers")
        Container(auth_svc, "Auth Service", "Flask / Python 3.11", "POST /auth/signup  POST /auth/login  POST /auth/logout  GET /auth/me")
        Container(users_svc, "Users Service", "Flask / Python 3.11", "GET|PUT /users/:id  GET /users/caretakers")
        Container(pets_svc, "Pets Service", "Flask / Python 3.11", "GET|POST /pets  GET|PUT|DELETE /pets/:id")
        Container(bookings_svc, "Bookings Service", "Flask / Python 3.11", "GET|POST /bookings  DELETE /bookings/:id  POST /bookings/:id/apply  POST /bookings/:id/confirm")
        Container(shared, "Shared Library", "Python module", "jwt_middleware — @jwt_required / @role_required decorators. email_service — SMTP wrapper (Gmail / Google Workspace).")
    }

    System_Ext(supabase, "Supabase", "Postgres + GoTrue Auth + RLS")
    System_Ext(smtp, "SMTP / Gmail", "Email delivery via STARTTLS")

    Rel(owner, frontend, "Uses", "HTTPS :3000")
    Rel(caretaker, frontend, "Uses", "HTTPS :3000")
    Rel(frontend, gateway, "API requests", "HTTP :8080 /api/*")

    Rel(gateway, auth_svc, "Proxy /auth/*", "HTTP :5001")
    Rel(gateway, users_svc, "Proxy /users/*", "HTTP :5002")
    Rel(gateway, pets_svc, "Proxy /pets/*", "HTTP :5003")
    Rel(gateway, bookings_svc, "Proxy /bookings/*", "HTTP :5004")

    Rel(auth_svc, shared, "Imports")
    Rel(users_svc, shared, "Imports")
    Rel(pets_svc, shared, "Imports")
    Rel(bookings_svc, shared, "Imports")

    Rel(auth_svc, supabase, "sign_up / sign_in_with_password / DB queries", "HTTPS REST")
    Rel(users_svc, supabase, "DB queries", "HTTPS REST")
    Rel(pets_svc, supabase, "DB queries", "HTTPS REST")
    Rel(bookings_svc, supabase, "DB queries", "HTTPS REST")
    Rel(shared, supabase, "Token validation — GET /auth/v1/user", "HTTPS REST")
    Rel(bookings_svc, smtp, "Send outcome emails", "SMTP / STARTTLS")
```

### Level 3 — Component Diagram (Bookings Service)

```mermaid
C4Component
    title Bookings Service — Component Diagram

    Container_Ext(gateway, "nginx Gateway")
    Container_Ext(supabase, "Supabase")
    Container_Ext(smtp, "SMTP / Gmail")

    Container_Boundary(bookings, "Bookings Service") {
        Component(bookings_res, "Bookings Resource", "Flask-RESTful Resource", "GET /bookings — list all (owner: own, caretaker: open)\nPOST /bookings — create a new booking (owner only)")
        Component(booking_res, "Booking Resource", "Flask-RESTful Resource", "GET /bookings/:id — fetch single booking with pets + applications\nDELETE /bookings/:id — cancel booking (owner only)")
        Component(apply_res, "Apply Resource", "Flask-RESTful Resource", "POST /bookings/:id/apply — caretaker submits an application")
        Component(confirm_res, "Confirm Resource", "Flask-RESTful Resource", "POST /bookings/:id/confirm — owner accepts one application, rejects others, triggers emails")
        Component(jwt_mw, "JWT Middleware", "Shared Python module", "@jwt_required — validates Bearer token\n@role_required — enforces owner / caretaker roles")
        Component(email_svc, "Email Service", "Shared Python module", "send_applicant_confirmed_email\nsend_applicant_rejected_email")
    }

    Rel(gateway, bookings_res, "POST / GET /bookings")
    Rel(gateway, booking_res, "GET / DELETE /bookings/:id")
    Rel(gateway, apply_res, "POST /bookings/:id/apply")
    Rel(gateway, confirm_res, "POST /bookings/:id/confirm")

    Rel(bookings_res, jwt_mw, "Decorated by")
    Rel(booking_res, jwt_mw, "Decorated by")
    Rel(apply_res, jwt_mw, "Decorated by")
    Rel(confirm_res, jwt_mw, "Decorated by")

    Rel(jwt_mw, supabase, "Verify token — GET /auth/v1/user")
    Rel(bookings_res, supabase, "INSERT / SELECT bookings")
    Rel(booking_res, supabase, "SELECT / DELETE bookings + applications")
    Rel(apply_res, supabase, "INSERT applications")
    Rel(confirm_res, supabase, "UPDATE bookings + applications")
    Rel(confirm_res, email_svc, "Notify caretakers")
    Rel(email_svc, smtp, "sendmail via STARTTLS")
```

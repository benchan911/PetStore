# Swagger / OpenAPI Documentation

The backend API is fully documented in OpenAPI 3.0 format.

## Files

- `openapi.yaml` - Complete OpenAPI specification for the CarePets API

## Quick Start

### Option 1: Online Swagger Editor (Fastest)

1. Open https://editor.swagger.io/
2. Paste the contents of `openapi.yaml` into the editor
3. Test against your local backend at `http://localhost:8080`

### Option 2: Run Swagger UI Locally with Docker

```bash
docker run --rm -p 8081:8080 \
  -e SWAGGER_JSON=/foo/openapi.yaml \
  -v "$(pwd)/docs/swagger:/foo" \
  swaggerapi/swagger-ui
```

Then open http://localhost:8081

## API Overview

### Base URL

- **Local**: `http://localhost:8080`
- **Production**: Replace with your deployed gateway domain

### Authentication

Most endpoints require Bearer JWT authentication:

1. Call `/api/auth/login` with email/password to get `access_token`
2. Click **Authorize** in Swagger UI
3. Enter: `Bearer <access_token>`
4. All subsequent requests will include the token

### Main Endpoints

| Resource                                       | Methods          | Description                                     |
| ---------------------------------------------- | ---------------- | ----------------------------------------------- |
| `/api/auth/*`                                  | POST             | Signup, login, logout, get current user profile |
| `/api/users/{user_id}`                         | GET, PUT         | View/update user profile                        |
| `/api/users/caretakers`                        | GET              | List all caretakers                             |
| `/api/pets`                                    | GET, POST        | List/create pets owned by current user          |
| `/api/pets/{pet_id}`                           | GET, PUT, DELETE | View/update/delete a pet                        |
| `/api/bookings`                                | GET, POST        | List/create bookings                            |
| `/api/bookings/{booking_id}`                   | GET, DELETE      | View/cancel a booking                           |
| `/api/bookings/{booking_id}/apply`             | POST             | Apply to a booking (caretaker)                  |
| `/api/bookings/{booking_id}/confirm`           | POST             | Confirm application (owner)                     |
| `/api/bookings/{booking_id}/applications/{id}` | DELETE           | Withdraw/reject application                     |

## Testing Flow

1. **Signup**: POST `/api/auth/signup` with role `owner` or `caretaker`
2. **Login**: POST `/api/auth/login` to get token
3. **Authenticate**: Click Authorize and paste token
4. **Owners**: Try `/api/pets` (POST) to create a pet, then `/api/bookings` (POST) to create a booking
5. **Caretakers**: Try `/api/users/caretakers` (GET), then `/api/bookings/{id}/apply` (POST) to apply

## Schema Types

- `Profile` - User profile with role, name, email
- `Pet` - Pet CRUD object with owner_id, species, name, etc.
- `Booking` - Booking object with status (open/confirmed/cancelled)
- `Application` - Application status (pending/accepted/rejected/withdrawn)

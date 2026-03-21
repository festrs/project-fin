# Simple Login System Design

## Overview

Add email + password authentication to the portfolio management app. Users are seeded (no registration). Sessions use JWT tokens stored in localStorage with 30-day expiry.

## Backend Changes

### 1. Dependencies

Add to `requirements.txt`:
- `python-jose[cryptography]` — JWT encoding/decoding
- `passlib[bcrypt]` — password hashing

### 2. User Model Update

Add `password_hash` field to the existing `User` model in `backend/app/models/user.py`:

```python
password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
```

### 3. Configuration

Add to `backend/app/config.py` (Settings class):

```python
jwt_secret_key: str = "change-me-in-production"
jwt_expiration_days: int = 30
default_user_password: str = "changeme"
```

`JWT_SECRET_KEY` and `DEFAULT_USER_PASSWORD` should be set in `.env`.

### 4. Auth Service

New file: `backend/app/services/auth.py`

Responsibilities:
- `hash_password(password: str) -> str` — bcrypt hash
- `verify_password(plain: str, hashed: str) -> bool` — bcrypt verify
- `create_access_token(user_id: str) -> str` — encode JWT with `sub=user_id`, `exp=now+30d`
- `decode_access_token(token: str) -> str` — decode JWT, return user_id or raise

### 5. Auth Dependency

New FastAPI dependency to replace the `X-User-Id` header pattern:

```python
def get_current_user_id(authorization: str = Header()) -> str:
    # Extract "Bearer <token>" from Authorization header
    # Decode JWT, return user_id
    # Raise HTTPException(401) on invalid/expired token
```

This replaces all existing `x_user_id: str = Header()` parameters across every router.

### 6. Auth Router

New file: `backend/app/routers/auth.py`

Single endpoint:

```
POST /api/auth/login
Body: { "email": str, "password": str }
Response: { "access_token": str, "token_type": "bearer", "user": { "id": str, "name": str, "email": str } }
Errors: 401 if email not found or password wrong
```

### 7. Auth Schemas

New file: `backend/app/schemas/auth.py`

```python
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo

class UserInfo(BaseModel):
    id: str
    name: str
    email: str
```

### 8. Seed Update

Update `backend/app/seed.py` to hash the default password when creating the seeded user:

```python
from app.services.auth import hash_password

user = User(
    id="ec92fcc7-1a95-4fa5-9911-7b88857cc524",
    name="Felipe",
    email="felipe@example.com",
    password_hash=hash_password(settings.default_user_password),
)
```

### 9. Router Migration

All routers currently use `x_user_id: str = Header()`. Replace with:

```python
from app.services.auth import get_current_user_id

# Before
async def get_portfolio(x_user_id: str = Header(), ...):

# After
async def get_portfolio(user_id: str = Depends(get_current_user_id), ...):
```

Affected routers: all files in `backend/app/routers/`.

## Frontend Changes

### 1. Auth Service

Add to `frontend/src/services/api.ts`:
- `login(email: string, password: string)` — calls `POST /api/auth/login`
- Store JWT in localStorage under key `auth_token`
- Store user info in localStorage under key `auth_user`
- Configure Axios interceptor to read token from localStorage and set `Authorization: Bearer <token>` header
- Remove the hardcoded `X-User-Id` header
- Add response interceptor: on 401, clear localStorage and redirect to `/login`

### 2. Auth Hook

New file: `frontend/src/hooks/useAuth.ts`

```typescript
function useAuth() {
  return {
    user: UserInfo | null,      // from localStorage
    isAuthenticated: boolean,    // token exists
    login(email, password),      // call API, store token
    logout(),                    // clear localStorage, redirect
  }
}
```

### 3. Login Page

New file: `frontend/src/pages/Login.tsx`

Simple form with:
- Email input
- Password input
- Submit button
- Error message display
- On success: redirect to `/` (Dashboard)
- Styled consistent with the existing glass-morphism theme

### 4. Route Guard

Update `frontend/src/App.tsx`:
- Add a `ProtectedRoute` wrapper that checks for token in localStorage
- If no token, redirect to `/login`
- `/login` route is public (no guard)

### 5. Logout

Add a logout button to the sidebar (below existing navigation). Clears token and redirects to `/login`.

## Data Flow

```
Login:
  User → Login page → POST /api/auth/login → verify bcrypt → JWT(user_id, exp=30d) → localStorage

Authenticated requests:
  Axios interceptor → reads localStorage → Authorization: Bearer <token>
  → FastAPI dependency → decode JWT → user_id → router logic

Token expired / invalid:
  401 response → Axios interceptor → clear localStorage → redirect /login

Logout:
  Sidebar button → clear localStorage → redirect /login
```

## Database Migration

Since the app uses `Base.metadata.create_all()` on startup and SQLite, adding the `password_hash` column requires either:
- **Option A:** Delete and recreate the DB (acceptable for dev — seed recreates data)
- **Option B:** Add an alembic migration

Recommendation: Option A for simplicity. The seed script recreates all data anyway.

## Testing

### Backend
- `tests/test_services/test_auth.py` — unit tests for hash, verify, JWT create/decode
- `tests/test_routers/test_auth.py` — login endpoint tests (success, wrong password, unknown email)
- Update existing router tests to use JWT auth instead of X-User-Id header

### Frontend
- `src/pages/__tests__/Login.test.tsx` — render, submit, error display
- `src/hooks/__tests__/useAuth.test.ts` — login, logout, token management

## Security Notes

- Passwords hashed with bcrypt (passlib)
- JWT signed with HS256 using a configurable secret key
- No sensitive data in JWT payload (only user_id and expiry)
- 401 on all endpoints if token missing/invalid/expired
- This is appropriate for a personal/small-team tool, not a public-facing production auth system

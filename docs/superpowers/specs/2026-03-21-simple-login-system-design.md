# Simple Login System Design

## Overview

Add email + password authentication to the portfolio management app. Users are seeded (no registration). Sessions use JWT tokens stored in localStorage with 30-day expiry.

## Backend Changes

### 1. Dependencies

Add to `requirements.txt`:
- `PyJWT[crypto]` — JWT encoding/decoding (actively maintained alternative to python-jose)
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

New file: `backend/app/dependencies.py`

FastAPI dependency to replace the `X-User-Id` header pattern. Lives in its own module to keep services free of FastAPI imports:

```python
def get_current_user_id(authorization: str = Header()) -> str:
    # Extract "Bearer <token>" from Authorization header
    # Decode JWT via auth service, return user_id
    # Raise HTTPException(401) on invalid/expired token
```

This replaces all existing `x_user_id: str = Header()` parameters across affected routers.

### 6. Auth Router

New file: `backend/app/routers/auth.py`

Single endpoint:

```
POST /api/auth/login
Body: { "email": str, "password": str }
Response: { "access_token": str, "token_type": "bearer", "user": { "id": str, "name": str, "email": str } }
Errors: 401 if email not found or password wrong
Rate limit: stricter than general CRUD (e.g., 5/minute) to mitigate brute-force
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

Update `backend/app/seed.py` in the `_seed_from_json` function where the user is created from `data["user"]`. Add `password_hash` using the configured default password:

```python
from app.services.auth import hash_password

# In _seed_from_json, after reading user_data from JSON:
user = User(
    id=user_data["id"],
    name=user_data["name"],
    email=user_data["email"],
    password_hash=hash_password(settings.default_user_password),
)
```

The password comes from `settings.default_user_password` (not the JSON file).

### 9. Router Migration

All routers currently use `x_user_id: str = Header()`. Replace with:

```python
from app.dependencies import get_current_user_id

# Before
async def get_portfolio(x_user_id: str = Header(), ...):

# After
async def get_portfolio(user_id: str = Depends(get_current_user_id), ...):
```

Affected routers (those using `x_user_id: str = Header()`):
- `asset_classes.py`
- `asset_weights.py`
- `transactions.py`
- `portfolio.py`
- `recommendations.py`
- `quarantine.py`
- `fundamentals.py`
- `splits.py`
- `dividends.py`

**Not affected** (no user context): `stocks.py`, `crypto.py`, health endpoint.

## Frontend Changes

### 1. Auth Service

Add to `frontend/src/services/api.ts`:
- `login(email: string, password: string)` — calls `POST /api/auth/login`
- Store JWT in localStorage under key `auth_token`
- Store user info in localStorage under key `auth_user`
- Configure Axios interceptor to read token from localStorage and set `Authorization: Bearer <token>` header
- Remove the hardcoded `X-User-Id` header
- Add response interceptor: on 401, clear localStorage and redirect to `/login` (skip this for `/api/auth/login` requests to avoid redirect loops on bad credentials)

### 2. Auth Context & Hook

New file: `frontend/src/contexts/AuthContext.tsx`

React Context provider wrapping the app so auth state is shared reactively across components (ProtectedRoute, Sidebar logout, etc.):

```typescript
// AuthProvider wraps <App /> in main.tsx
// useAuth() hook reads from context

interface AuthContextValue {
  user: UserInfo | null;
  isAuthenticated: boolean;
  login(email: string, password: string): Promise<void>;
  logout(): void;
}
```

Add `UserInfo` and `LoginResponse` types to `frontend/src/types/index.ts`.

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

The codebase already has a migration system in `backend/app/migrations/__init__.py` with a `_MIGRATIONS` list. Add a new migration function (e.g., `_002_add_password_hash`) that:

1. `ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''`
2. Backfills existing users with a hashed version of `settings.default_user_password`

This is consistent with the existing migration approach and avoids data loss.

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
- 30-day token expiry with no refresh — user will need to re-login after 30 days (acceptable for this use case)

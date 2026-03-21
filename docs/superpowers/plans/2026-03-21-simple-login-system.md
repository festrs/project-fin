# Simple Login System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email + password authentication with JWT tokens so the app has a real login flow instead of a hardcoded user ID.

**Architecture:** Backend auth service (password hashing + JWT) with a FastAPI dependency replacing the `X-User-Id` header pattern. Frontend AuthContext + login page with Axios interceptors for token management.

**Tech Stack:** PyJWT, passlib[bcrypt], React Context API

**Spec:** `docs/superpowers/specs/2026-03-21-simple-login-system-design.md`

---

### Task 1: Add Dependencies and Configuration

**Files:**
- Modify: `backend/requirements.txt:13` (append new deps)
- Modify: `backend/app/config.py:19-21` (add auth settings)
- Modify: `backend/app/middleware/rate_limit.py:6` (add login rate limit)

- [ ] **Step 1: Add PyJWT and passlib to requirements.txt**

Append to `backend/requirements.txt`:

```
PyJWT[crypto]==2.9.0
passlib[bcrypt]==1.7.4
```

- [ ] **Step 2: Add auth settings to config.py**

Add after line 19 (`split_checker_hour`) in `backend/app/config.py`:

```python
    jwt_secret_key: str = "change-me-in-production"
    jwt_expiration_days: int = 30
    default_user_password: str = "changeme"
```

- [ ] **Step 3: Add login rate limit constant**

Add to `backend/app/middleware/rate_limit.py`:

```python
LOGIN_LIMIT = "5/minute"
```

- [ ] **Step 4: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/middleware/rate_limit.py
git commit -m "feat(auth): add JWT and bcrypt dependencies and config"
```

---

### Task 2: Auth Service (Password Hashing + JWT)

**Files:**
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_services/test_auth.py`

- [ ] **Step 1: Write failing tests for auth service**

Create `backend/tests/test_services/test_auth.py`:

```python
import pytest
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token("user-123")
    assert isinstance(token, str)
    user_id = decode_access_token(token)
    assert user_id == "user-123"


def test_decode_access_token_invalid():
    with pytest.raises(Exception):
        decode_access_token("invalid.token.here")


def test_decode_access_token_expired():
    import jwt as pyjwt
    from datetime import datetime, timedelta
    from app.config import settings

    # Create a token that expired in the past
    past = datetime.utcnow() - timedelta(days=1)
    payload = {"sub": "user-123", "exp": past}
    token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

    with pytest.raises(Exception):
        decode_access_token(token)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_services/test_auth.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement auth service**

Create `backend/app/services/auth.py`:

```python
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_expiration_days)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    if user_id is None:
        raise ValueError("Invalid token: no subject")
    return user_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_services/test_auth.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth.py backend/tests/test_services/test_auth.py
git commit -m "feat(auth): add auth service with password hashing and JWT"
```

---

### Task 3: User Model Update and Database Migration

**Files:**
- Modify: `backend/app/models/user.py:15` (add password_hash field)
- Modify: `backend/app/migrations/__init__.py:139-141` (add migration)

> **Why this comes before the login router:** The login router tests create `User` objects with `password_hash`, so the model field must exist first.

- [ ] **Step 1: Add password_hash to User model**

Add after line 15 (`email` field) in `backend/app/models/user.py`:

```python
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
```

- [ ] **Step 2: Add database migration**

Add to `backend/app/migrations/__init__.py`, before the `_MIGRATIONS` list:

```python
def _002_add_password_hash(cur: sqlite3.Cursor) -> None:
    """Add password_hash column to users table."""
    if not _table_exists(cur, "users"):
        return

    columns = _get_columns(cur, "users")
    if "password_hash" in columns:
        return

    cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")

    # Backfill existing users with hashed default password
    from app.services.auth import hash_password
    from app.config import settings
    default_hash = hash_password(settings.default_user_password)
    cur.execute("UPDATE users SET password_hash = ?", (default_hash,))
```

Update the `_MIGRATIONS` list:

```python
_MIGRATIONS = [
    _001_decimal_money,
    _002_add_password_hash,
]
```

- [ ] **Step 3: Run all tests to verify nothing broke**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/user.py backend/app/migrations/__init__.py
git commit -m "feat(auth): add password_hash to User model with migration"
```

---

### Task 4: Auth Dependency (FastAPI)

**Files:**
- Create: `backend/app/dependencies.py`

- [ ] **Step 1: Create auth dependency module**

Create `backend/app/dependencies.py`:

```python
from fastapi import Header, HTTPException

from app.services.auth import decode_access_token


def get_current_user_id(authorization: str = Header()) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[len("Bearer "):]
    try:
        return decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat(auth): add FastAPI auth dependency for JWT validation"
```

---

### Task 5: Auth Schemas and Login Router

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py:161-177` (register auth router)
- Create: `backend/tests/test_routers/test_auth.py`

- [ ] **Step 1: Create auth schemas**

Create `backend/app/schemas/auth.py`:

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    id: str
    name: str
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo
```

- [ ] **Step 2: Write failing tests for login router**

Create `backend/tests/test_routers/test_auth.py`:

```python
from app.models.user import User
from app.services.auth import hash_password


def test_login_success(client, db):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpass",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"


def test_login_wrong_password(client, db):
    user = User(
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()

    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client, db):
    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "testpass",
    })
    assert resp.status_code == 401
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_routers/test_auth.py -v`
Expected: FAIL (no route)

- [ ] **Step 4: Implement login router**

Create `backend/app/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, LOGIN_LIMIT
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit(LOGIN_LIMIT)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return LoginResponse(
        access_token=token,
        user=UserInfo(id=user.id, name=user.name, email=user.email),
    )
```

- [ ] **Step 5: Register auth router in main.py**

In `backend/app/main.py`, add to the imports block (line 161):

```python
from app.routers import (
    asset_classes, asset_weights, transactions,
    stocks, crypto, portfolio, recommendations, quarantine,
    fundamentals, splits, dividends, auth,
)
```

Add before the other `include_router` calls (before line 167):

```python
app.include_router(auth.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_routers/test_auth.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/routers/auth.py backend/tests/test_routers/test_auth.py backend/app/main.py
git commit -m "feat(auth): add login endpoint with rate limiting"
```

---

### Task 6: Update Seed Script

**Files:**
- Modify: `backend/app/seed.py:61` (add password_hash to seeded user)

- [ ] **Step 1: Update _seed_from_json to include password_hash**

In `backend/app/seed.py`, add import at top:

```python
from app.services.auth import hash_password
from app.config import settings
```

Replace line 61:

```python
    user = User(id=user_data["id"], name=user_data["name"], email=user_data["email"])
```

With:

```python
    user = User(
        id=user_data["id"],
        name=user_data["name"],
        email=user_data["email"],
        password_hash=hash_password(settings.default_user_password),
    )
```

- [ ] **Step 2: Run all tests**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/seed.py
git commit -m "feat(auth): hash default password in seed script"
```

---

### Task 7: Update Test Conftest for Auth

**Files:**
- Modify: `backend/tests/conftest.py` (add auth helper fixtures)

- [ ] **Step 1: Update conftest with auth fixtures**

In `backend/tests/conftest.py`, update the `default_user` fixture to include `password_hash`, and add an `auth_headers` fixture:

```python
import os
os.environ["ENABLE_SCHEDULER"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth import hash_password, create_access_token

from fastapi.testclient import TestClient

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def default_user(db):
    user = User(
        name="Default User",
        email="default@example.com",
        password_hash=hash_password("testpass"),
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def auth_headers(default_user):
    token = create_access_token(default_user.id)
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "feat(auth): update test conftest with auth fixtures"
```

---

### Task 8: Migrate Backend Routers from X-User-Id to JWT

**Files:**
- Modify: `backend/app/routers/asset_classes.py`
- Modify: `backend/app/routers/asset_weights.py`
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/app/routers/portfolio.py`
- Modify: `backend/app/routers/recommendations.py`
- Modify: `backend/app/routers/quarantine.py`
- Modify: `backend/app/routers/fundamentals.py`
- Modify: `backend/app/routers/splits.py`
- Modify: `backend/app/routers/dividends.py`

For each router file listed above, apply the same pattern:

1. Replace `from fastapi import ..., Header, ...` with `from fastapi import ..., Depends, ...` (keep Depends if already there, remove Header if no longer used)
2. Add import: `from app.dependencies import get_current_user_id`
3. Replace every `x_user_id: str = Header()` parameter with `user_id: str = Depends(get_current_user_id)`
4. Replace every usage of `x_user_id` in the function body with `user_id`

- [ ] **Step 1: Migrate asset_classes.py**

Apply the pattern described above.

- [ ] **Step 2: Migrate asset_weights.py**

Apply the pattern described above.

- [ ] **Step 3: Migrate transactions.py**

Apply the pattern described above.

- [ ] **Step 4: Migrate portfolio.py**

Apply the pattern described above.

- [ ] **Step 5: Migrate recommendations.py**

Apply the pattern described above.

- [ ] **Step 6: Migrate quarantine.py**

Apply the pattern described above.

- [ ] **Step 7: Migrate fundamentals.py**

Apply the pattern described above.

- [ ] **Step 8: Migrate splits.py**

Apply the pattern described above.

- [ ] **Step 9: Migrate dividends.py**

Apply the pattern described above.

- [ ] **Step 10: Commit**

```bash
git add backend/app/routers/
git commit -m "feat(auth): migrate all routers from X-User-Id to JWT auth"
```

---

### Task 9: Update Existing Backend Tests to Use JWT Auth

**Files:**
- Modify: all test files in `backend/tests/` that use `X-User-Id` headers

The test files using `X-User-Id`:
- `backend/tests/test_e2e.py`
- `backend/tests/test_market_search.py`
- `backend/tests/test_portfolio_enriched.py`
- `backend/tests/test_asset_class_type.py`
- `backend/tests/test_routers/test_recommendations.py`
- `backend/tests/test_routers/test_portfolio.py`
- `backend/tests/test_routers/test_fundamentals.py`
- `backend/tests/test_routers/test_transactions.py`
- `backend/tests/test_routers/test_quarantine.py`
- `backend/tests/test_routers/test_splits.py`
- `backend/tests/test_routers/test_asset_classes.py`
- `backend/tests/test_routers/test_asset_weights.py`

For each test file:

1. Import `create_access_token` from `app.services.auth`
2. Replace `headers = {"X-User-Id": user.id}` with:
   ```python
   token = create_access_token(user.id)
   headers = {"Authorization": f"Bearer {token}"}
   ```
3. For tests using `default_user` fixture, use the `auth_headers` fixture instead where possible.
4. For `test_market_search.py` (stocks/crypto endpoints): these routers don't use auth, so the `X-User-Id` header can simply be removed (cleanup only — it was already ignored).
5. **Special case:** `test_asset_class_type.py` uses hardcoded `"default-user-id"` instead of a `default_user` fixture. Create a user with `password_hash` in the test and generate a JWT token from it.

- [ ] **Step 1: Update test_portfolio.py**

Replace `X-User-Id` headers with JWT Authorization headers using `auth_headers` fixture.

- [ ] **Step 2: Update test_recommendations.py**

Same pattern.

- [ ] **Step 3: Update test_fundamentals.py**

Same pattern.

- [ ] **Step 4: Update test_transactions.py**

Same pattern.

- [ ] **Step 5: Update test_quarantine.py**

Same pattern.

- [ ] **Step 6: Update test_splits.py**

Same pattern.

- [ ] **Step 7: Update test_asset_classes.py**

Same pattern.

- [ ] **Step 8: Update test_asset_weights.py**

Same pattern.

- [ ] **Step 9: Update test_portfolio_enriched.py**

Same pattern.

- [ ] **Step 10: Update test_asset_class_type.py**

Special case: create a user with `password_hash` and generate a JWT token (no `default_user` fixture available).

- [ ] **Step 11: Update test_e2e.py**

Same pattern.

- [ ] **Step 12: Update test_market_search.py**

Remove `X-User-Id` headers (stocks/crypto don't require auth — cleanup only).

- [ ] **Step 13: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 14: Commit**

```bash
git add backend/tests/
git commit -m "feat(auth): update all tests to use JWT auth headers"
```

---

### Task 10: Frontend Auth Types and API Service

**Files:**
- Modify: `frontend/src/types/index.ts:151` (append auth types)
- Modify: `frontend/src/services/api.ts` (replace hardcoded header with interceptors)

- [ ] **Step 1: Add auth types to types/index.ts**

Append to `frontend/src/types/index.ts`:

```typescript
export interface UserInfo {
  id: string;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}
```

- [ ] **Step 2: Update api.ts with auth interceptors**

Replace entire `frontend/src/services/api.ts`:

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: redirect to login on 401 (skip for login requests)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      !error.config?.url?.includes("/auth/login")
    ) {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat(auth): add auth types and JWT interceptors to API service"
```

---

### Task 11: AuthContext Provider

**Files:**
- Create: `frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Create AuthContext**

Create `frontend/src/contexts/AuthContext.tsx`:

```typescript
import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import api from "../services/api";
import type { UserInfo, LoginResponse } from "../types";

interface AuthContextValue {
  user: UserInfo | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(getStoredUser);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<LoginResponse>("/auth/login", { email, password });
    localStorage.setItem("auth_token", data.access_token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx
git commit -m "feat(auth): add AuthContext provider and useAuth hook"
```

---

### Task 12: Login Page

**Files:**
- Create: `frontend/src/pages/Login.tsx`

- [ ] **Step 1: Create Login page**

Create `frontend/src/pages/Login.tsx`:

```typescript
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-bg-page flex items-center justify-center">
      <div className="glass-card p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-text-primary mb-6 text-center">
          Project <span className="text-primary">Fin</span>
        </h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="glass-input px-3 py-2 rounded-lg text-text-primary bg-[var(--glass-input-bg)] border border-[var(--glass-border)] outline-none focus:border-primary"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="glass-input px-3 py-2 rounded-lg text-text-primary bg-[var(--glass-input-bg)] border border-[var(--glass-border)] outline-none focus:border-primary"
          />
          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading}
            className="bg-primary text-white py-2 rounded-lg font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat(auth): add Login page with glass-morphism styling"
```

---

### Task 13: Route Guard and App Integration

**Files:**
- Modify: `frontend/src/App.tsx` (add ProtectedRoute, login route)
- Modify: `frontend/src/main.tsx` (wrap with AuthProvider)
- Modify: `frontend/src/components/Sidebar.tsx` (add logout button)

- [ ] **Step 1: Update App.tsx with route guard**

Replace `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import AssetClassHoldings from "./pages/AssetClassHoldings";
import Invest from "./pages/Invest";
import Login from "./pages/Login";
import { useAuth } from "./contexts/AuthContext";

function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-screen bg-bg-page flex">
      <Sidebar />
      <main className="ml-[220px] w-[calc(100%-220px)] px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invest" element={<Invest />} />
          <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 2: Wrap App with AuthProvider in main.tsx**

Replace `frontend/src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
```

- [ ] **Step 3: Add logout button to Sidebar**

Replace `frontend/src/components/Sidebar.tsx`:

```typescript
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutGrid, TrendingUp, Settings, LogOut } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/invest", label: "Where to Invest", icon: TrendingUp },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-[var(--glass-sidebar-bg)] border-r border-[var(--glass-border)] p-6 flex flex-col gap-1">
      <Link to="/" className="text-2xl font-bold text-text-primary px-3 mb-6 tracking-[-0.3px]">
        Project <span className="text-primary">Fin</span>
      </Link>
      {links.map((link) => {
        const isActive = location.pathname === link.to;
        return (
          <Link
            key={link.to}
            to={link.to}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium transition-colors ${
              isActive
                ? "bg-[var(--glass-primary-soft)] text-primary font-semibold"
                : "text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary"
            }`}
          >
            <link.icon size={18} strokeWidth={1.8} />
            {link.label}
          </Link>
        );
      })}
      <button
        onClick={handleLogout}
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary transition-colors mt-auto"
      >
        <LogOut size={18} strokeWidth={1.8} />
        Logout
      </button>
    </nav>
  );
}
```

- [ ] **Step 4: Run frontend build to check for type errors**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat(auth): add route guard, AuthProvider, and logout button"
```

---

### Task 14: Frontend Tests

**Files:**
- Create: `frontend/src/pages/__tests__/Login.test.tsx`

- [ ] **Step 1: Write Login page tests**

Create `frontend/src/pages/__tests__/Login.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../../contexts/AuthContext";
import Login from "../Login";
import { vi } from "vitest";
import api from "../../services/api";

vi.mock("../../services/api");

const mockedApi = vi.mocked(api);

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("Login", () => {
  it("renders email and password inputs", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    mockedApi.post.mockRejectedValueOnce(new Error("401"));
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText("Email"), {
      target: { value: "bad@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: Tests pass

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/__tests__/Login.test.tsx
git commit -m "test(auth): add Login page tests"
```

---

### Task 15: End-to-End Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: All PASS

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Manual smoke test (optional)**

Start backend and frontend in separate terminals:
```bash
# Terminal 1
cd backend && python -m uvicorn app.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

1. Navigate to `http://localhost:5173` — should redirect to `/login`
2. Enter email `felipe@example.com` and password `changeme` — should redirect to dashboard
3. Click Logout in sidebar — should redirect to `/login`
4. Try accessing `/` directly — should redirect to `/login`

- [ ] **Step 5: Final commit if any fixes needed**

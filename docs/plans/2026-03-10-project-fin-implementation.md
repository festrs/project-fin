# Project Fin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a financial dashboard for tracking US/BR stocks and crypto with portfolio management, ledger, rebalancing recommendations, and quarantine system.

**Architecture:** Monorepo with FastAPI backend (SQLAlchemy + SQLite) and React frontend (Vite + Recharts + TailwindCSS). Separate builds, deployed as two Render services.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite, pytest, React 18, TypeScript, Vite, Recharts, TailwindCSS, Vitest, Axios

---

## Phase 1: Backend Foundation

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/routers backend/app/services backend/app/middleware backend/tests
```

**Step 2: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
pydantic==2.10.3
pydantic-settings==2.7.0
slowapi==0.1.9
cachetools==5.5.0
yfinance==0.2.51
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
```

**Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./project_fin.db"
    cors_origin: str = "http://localhost:5173"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 4: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 5: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Project Fin", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Step 6: Create conftest.py with test DB fixture**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

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
```

**Step 7: Write health check test**

```python
# backend/tests/test_health.py
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

**Step 8: Run test**

Run: `cd backend && pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: PASS

**Step 9: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, SQLAlchemy, pytest"
```

---

### Task 2: User model

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/tests/test_models/__init__.py`
- Create: `backend/tests/test_models/test_user.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models/test_user.py
from app.models.user import User


def test_create_user(db):
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.created_at is not None


def test_user_email_unique(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    user1 = User(name="User 1", email="same@example.com")
    user2 = User(name="User 2", email="same@example.com")
    db.add(user1)
    db.commit()
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models/test_user.py -v`
Expected: FAIL — ImportError

**Step 3: Implement User model**

```python
# backend/app/models/__init__.py
from app.models.user import User

__all__ = ["User"]
```

```python
# backend/app/models/user.py
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

```python
# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    email: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models/test_user.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/ backend/tests/test_models/
git commit -m "feat: add User model with unique email constraint"
```

---

### Task 3: AssetClass model

**Files:**
- Create: `backend/app/models/asset_class.py`
- Create: `backend/app/schemas/asset_class.py`
- Create: `backend/tests/test_models/test_asset_class.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models/test_asset_class.py
from app.models.user import User
from app.models.asset_class import AssetClass


def test_create_asset_class(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=40.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)

    assert ac.id is not None
    assert ac.name == "US Stocks"
    assert ac.target_weight == 40.0
    assert ac.user_id == user.id


def test_asset_class_default_weight(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="Crypto")
    db.add(ac)
    db.commit()
    db.refresh(ac)

    assert ac.target_weight == 0.0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models/test_asset_class.py -v`
Expected: FAIL

**Step 3: Implement AssetClass model**

```python
# backend/app/models/asset_class.py
import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetClass(Base):
    __tablename__ = "asset_classes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    target_weight: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    assets = relationship("AssetWeight", back_populates="asset_class", cascade="all, delete-orphan")
```

```python
# backend/app/schemas/asset_class.py
from pydantic import BaseModel
from datetime import datetime


class AssetClassCreate(BaseModel):
    name: str
    target_weight: float = 0.0


class AssetClassUpdate(BaseModel):
    name: str | None = None
    target_weight: float | None = None


class AssetClassResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_weight: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

Update `backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.asset_class import AssetClass

__all__ = ["User", "AssetClass"]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models/test_asset_class.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add AssetClass model with target weight"
```

---

### Task 4: AssetWeight model

**Files:**
- Create: `backend/app/models/asset_weight.py`
- Create: `backend/app/schemas/asset_weight.py`
- Create: `backend/tests/test_models/test_asset_weight.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models/test_asset_weight.py
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight


def test_create_asset_weight(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=40.0)
    db.add(ac)
    db.commit()

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=50.0)
    db.add(aw)
    db.commit()
    db.refresh(aw)

    assert aw.id is not None
    assert aw.symbol == "AAPL"
    assert aw.target_weight == 50.0
    assert aw.asset_class_id == ac.id


def test_asset_weight_relationship(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks")
    db.add(ac)
    db.commit()

    aw1 = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=50.0)
    aw2 = AssetWeight(asset_class_id=ac.id, symbol="MSFT", target_weight=50.0)
    db.add_all([aw1, aw2])
    db.commit()
    db.refresh(ac)

    assert len(ac.assets) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models/test_asset_weight.py -v`
Expected: FAIL

**Step 3: Implement AssetWeight model**

```python
# backend/app/models/asset_weight.py
import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetWeight(Base):
    __tablename__ = "asset_weights"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    asset_class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_classes.id")
    )
    symbol: Mapped[str] = mapped_column(String(20))
    target_weight: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    asset_class = relationship("AssetClass", back_populates="assets")
```

```python
# backend/app/schemas/asset_weight.py
from pydantic import BaseModel
from datetime import datetime


class AssetWeightCreate(BaseModel):
    symbol: str
    target_weight: float = 0.0


class AssetWeightUpdate(BaseModel):
    target_weight: float


class AssetWeightResponse(BaseModel):
    id: str
    asset_class_id: str
    symbol: str
    target_weight: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

Update `backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight

__all__ = ["User", "AssetClass", "AssetWeight"]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models/test_asset_weight.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add AssetWeight model linked to AssetClass"
```

---

### Task 5: Transaction model

**Files:**
- Create: `backend/app/models/transaction.py`
- Create: `backend/app/schemas/transaction.py`
- Create: `backend/tests/test_models/test_transaction.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models/test_transaction.py
from datetime import date

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction


def test_create_buy_transaction(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks")
    db.add(ac)
    db.commit()

    tx = Transaction(
        user_id=user.id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10.0,
        unit_price=150.0,
        total_value=1500.0,
        currency="USD",
        tax_amount=5.0,
        date=date(2026, 1, 15),
        notes="First purchase",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    assert tx.id is not None
    assert tx.type == "buy"
    assert tx.quantity == 10.0
    assert tx.total_value == 1500.0
    assert tx.currency == "USD"


def test_create_dividend_transaction(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks")
    db.add(ac)
    db.commit()

    tx = Transaction(
        user_id=user.id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="dividend",
        quantity=0,
        unit_price=0,
        total_value=25.0,
        currency="USD",
        tax_amount=3.75,
        date=date(2026, 3, 1),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    assert tx.type == "dividend"
    assert tx.quantity == 0
    assert tx.total_value == 25.0


def test_filter_transactions_by_type(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks")
    db.add(ac)
    db.commit()

    for t in ["buy", "buy", "sell", "dividend"]:
        tx = Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
            type=t, quantity=1, unit_price=100, total_value=100,
            currency="USD", tax_amount=0, date=date(2026, 1, 1),
        )
        db.add(tx)
    db.commit()

    buys = db.query(Transaction).filter_by(type="buy").all()
    assert len(buys) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models/test_transaction.py -v`
Expected: FAIL

**Step 3: Implement Transaction model**

```python
# backend/app/models/transaction.py
import uuid
from datetime import datetime, date as date_type

from sqlalchemy import String, Float, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    asset_class_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("asset_classes.id")
    )
    asset_symbol: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(
        Enum("buy", "sell", "dividend", name="transaction_type")
    )
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[float] = mapped_column(Float)
    total_value: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(Enum("BRL", "USD", name="currency_type"))
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    date: Mapped[date_type] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

```python
# backend/app/schemas/transaction.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Literal


class TransactionCreate(BaseModel):
    asset_class_id: str
    asset_symbol: str
    type: Literal["buy", "sell", "dividend"]
    quantity: float
    unit_price: float
    total_value: float
    currency: Literal["BRL", "USD"]
    tax_amount: float = 0.0
    date: date
    notes: str | None = None


class TransactionUpdate(BaseModel):
    quantity: float | None = None
    unit_price: float | None = None
    total_value: float | None = None
    tax_amount: float | None = None
    date: date | None = None
    notes: str | None = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    asset_class_id: str
    asset_symbol: str
    type: str
    quantity: float
    unit_price: float
    total_value: float
    currency: str
    tax_amount: float
    date: date
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

Update `backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction

__all__ = ["User", "AssetClass", "AssetWeight", "Transaction"]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models/test_transaction.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add Transaction model for buy/sell/dividend ledger"
```

---

### Task 6: QuarantineConfig model

**Files:**
- Create: `backend/app/models/quarantine_config.py`
- Create: `backend/app/schemas/quarantine.py`
- Create: `backend/tests/test_models/test_quarantine.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models/test_quarantine.py
from app.models.user import User
from app.models.quarantine_config import QuarantineConfig


def test_create_quarantine_config(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    qc = QuarantineConfig(user_id=user.id)
    db.add(qc)
    db.commit()
    db.refresh(qc)

    assert qc.threshold == 2
    assert qc.period_days == 180


def test_custom_quarantine_config(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    qc = QuarantineConfig(user_id=user.id, threshold=3, period_days=90)
    db.add(qc)
    db.commit()
    db.refresh(qc)

    assert qc.threshold == 3
    assert qc.period_days == 90
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models/test_quarantine.py -v`
Expected: FAIL

**Step 3: Implement QuarantineConfig model**

```python
# backend/app/models/quarantine_config.py
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QuarantineConfig(Base):
    __tablename__ = "quarantine_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)
    threshold: Mapped[int] = mapped_column(Integer, default=2)
    period_days: Mapped[int] = mapped_column(Integer, default=180)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

```python
# backend/app/schemas/quarantine.py
from pydantic import BaseModel
from datetime import datetime, date


class QuarantineConfigUpdate(BaseModel):
    threshold: int | None = None
    period_days: int | None = None


class QuarantineConfigResponse(BaseModel):
    id: str
    user_id: str
    threshold: int
    period_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuarantineStatusResponse(BaseModel):
    asset_symbol: str
    buy_count_in_period: int
    is_quarantined: bool
    quarantine_ends_at: date | None
```

Update `backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig

__all__ = ["User", "AssetClass", "AssetWeight", "Transaction", "QuarantineConfig"]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models/test_quarantine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add QuarantineConfig model with defaults"
```

---

## Phase 2: Backend Services

### Task 7: Market data service (yfinance + CoinGecko)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/market_data.py`
- Create: `backend/tests/test_services/__init__.py`
- Create: `backend/tests/test_services/test_market_data.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_market_data.py
from unittest.mock import patch, MagicMock

from app.services.market_data import MarketDataService


class TestStockData:
    @patch("app.services.market_data.yf.Ticker")
    def test_get_stock_quote(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "currentPrice": 150.0,
            "shortName": "Apple Inc.",
            "currency": "USD",
            "marketCap": 2500000000000,
        }
        mock_ticker_cls.return_value = mock_ticker

        service = MarketDataService()
        result = service.get_stock_quote("AAPL")

        assert result["current_price"] == 150.0
        assert result["name"] == "Apple Inc."
        assert result["currency"] == "USD"
        assert result["symbol"] == "AAPL"

    @patch("app.services.market_data.yf.Ticker")
    def test_get_stock_history(self, mock_ticker_cls):
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({
            "Close": [148.0, 149.0, 150.0],
            "Volume": [1000, 1100, 1200],
        }, index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
        mock_ticker_cls.return_value = mock_ticker

        service = MarketDataService()
        result = service.get_stock_history("AAPL", period="1mo")

        assert len(result) == 3
        assert result[0]["close"] == 148.0


class TestCryptoData:
    @patch("app.services.market_data.httpx.get")
    def test_get_crypto_quote(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "bitcoin": {
                    "usd": 65000.0,
                    "usd_market_cap": 1200000000000,
                    "usd_24h_change": 2.5,
                }
            },
        )

        service = MarketDataService()
        result = service.get_crypto_quote("bitcoin")

        assert result["current_price"] == 65000.0
        assert result["currency"] == "USD"

    @patch("app.services.market_data.httpx.get")
    def test_get_crypto_history(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "prices": [
                    [1704067200000, 64000.0],
                    [1704153600000, 65000.0],
                ]
            },
        )

        service = MarketDataService()
        result = service.get_crypto_history("bitcoin", days=30)

        assert len(result) == 2
        assert result[0]["price"] == 64000.0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_services/test_market_data.py -v`
Expected: FAIL

**Step 3: Implement market data service**

```python
# backend/app/services/market_data.py
from datetime import datetime

import httpx
import yfinance as yf
from cachetools import TTLCache

from app.config import settings

# Cache: stock quotes 5min, history 15min, crypto 2min
_stock_quote_cache = TTLCache(maxsize=100, ttl=300)
_stock_history_cache = TTLCache(maxsize=50, ttl=900)
_crypto_quote_cache = TTLCache(maxsize=50, ttl=120)
_crypto_history_cache = TTLCache(maxsize=50, ttl=900)


class MarketDataService:
    def get_stock_quote(self, symbol: str) -> dict:
        if symbol in _stock_quote_cache:
            return _stock_quote_cache[symbol]

        ticker = yf.Ticker(symbol)
        info = ticker.info
        result = {
            "symbol": symbol,
            "name": info.get("shortName", ""),
            "current_price": info.get("currentPrice", 0.0),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
        }
        _stock_quote_cache[symbol] = result
        return result

    def get_stock_history(self, symbol: str, period: str = "1mo") -> list[dict]:
        cache_key = f"{symbol}:{period}"
        if cache_key in _stock_history_cache:
            return _stock_history_cache[cache_key]

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        result = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": row["Close"],
                "volume": row.get("Volume", 0),
            }
            for idx, row in df.iterrows()
        ]
        _stock_history_cache[cache_key] = result
        return result

    def get_crypto_quote(self, coin_id: str) -> dict:
        if coin_id in _crypto_quote_cache:
            return _crypto_quote_cache[coin_id]

        url = f"{settings.coingecko_api_url}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_change": "true",
        }
        response = httpx.get(url, params=params)
        data = response.json()[coin_id]
        result = {
            "coin_id": coin_id,
            "current_price": data["usd"],
            "currency": "USD",
            "market_cap": data.get("usd_market_cap", 0),
            "change_24h": data.get("usd_24h_change", 0),
        }
        _crypto_quote_cache[coin_id] = result
        return result

    def get_crypto_history(self, coin_id: str, days: int = 30) -> list[dict]:
        cache_key = f"{coin_id}:{days}"
        if cache_key in _crypto_history_cache:
            return _crypto_history_cache[cache_key]

        url = f"{settings.coingecko_api_url}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": days}
        response = httpx.get(url, params=params)
        data = response.json()
        result = [
            {
                "date": datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d"),
                "price": price,
            }
            for ts, price in data["prices"]
        ]
        _crypto_history_cache[cache_key] = result
        return result
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_services/test_market_data.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add market data service with yfinance and CoinGecko"
```

---

### Task 8: Quarantine service

**Files:**
- Create: `backend/app/services/quarantine.py`
- Create: `backend/tests/test_services/test_quarantine.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_quarantine.py
from datetime import date, timedelta

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig
from app.services.quarantine import QuarantineService


def _create_user_and_class(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()
    ac = AssetClass(user_id=user.id, name="US Stocks")
    db.add(ac)
    db.commit()
    qc = QuarantineConfig(user_id=user.id)
    db.add(qc)
    db.commit()
    return user, ac


def _add_buy(db, user, ac, symbol, days_ago):
    tx = Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol=symbol,
        type="buy", quantity=1, unit_price=100, total_value=100,
        currency="USD", tax_amount=0, date=date.today() - timedelta(days=days_ago),
    )
    db.add(tx)
    db.commit()


def test_not_quarantined_with_one_buy(db):
    user, ac = _create_user_and_class(db)
    _add_buy(db, user, ac, "AAPL", days_ago=10)

    service = QuarantineService(db)
    status = service.get_asset_status(user.id, "AAPL")

    assert status.is_quarantined is False
    assert status.buy_count_in_period == 1


def test_quarantined_with_two_buys(db):
    user, ac = _create_user_and_class(db)
    _add_buy(db, user, ac, "AAPL", days_ago=10)
    _add_buy(db, user, ac, "AAPL", days_ago=5)

    service = QuarantineService(db)
    status = service.get_asset_status(user.id, "AAPL")

    assert status.is_quarantined is True
    assert status.buy_count_in_period == 2
    assert status.quarantine_ends_at is not None


def test_not_quarantined_if_buys_outside_period(db):
    user, ac = _create_user_and_class(db)
    _add_buy(db, user, ac, "AAPL", days_ago=200)
    _add_buy(db, user, ac, "AAPL", days_ago=190)

    service = QuarantineService(db)
    status = service.get_asset_status(user.id, "AAPL")

    assert status.is_quarantined is False
    assert status.buy_count_in_period == 0


def test_get_all_quarantine_statuses(db):
    user, ac = _create_user_and_class(db)
    _add_buy(db, user, ac, "AAPL", days_ago=10)
    _add_buy(db, user, ac, "AAPL", days_ago=5)
    _add_buy(db, user, ac, "MSFT", days_ago=10)

    service = QuarantineService(db)
    statuses = service.get_all_statuses(user.id)

    aapl = next(s for s in statuses if s.asset_symbol == "AAPL")
    msft = next(s for s in statuses if s.asset_symbol == "MSFT")

    assert aapl.is_quarantined is True
    assert msft.is_quarantined is False
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_services/test_quarantine.py -v`
Expected: FAIL

**Step 3: Implement quarantine service**

```python
# backend/app/services/quarantine.py
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.quarantine_config import QuarantineConfig
from app.models.transaction import Transaction


@dataclass
class QuarantineStatus:
    asset_symbol: str
    buy_count_in_period: int
    is_quarantined: bool
    quarantine_ends_at: date | None


class QuarantineService:
    def __init__(self, db: Session):
        self.db = db

    def _get_config(self, user_id: str) -> QuarantineConfig:
        config = self.db.query(QuarantineConfig).filter_by(user_id=user_id).first()
        if not config:
            config = QuarantineConfig(user_id=user_id)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def get_asset_status(self, user_id: str, symbol: str) -> QuarantineStatus:
        config = self._get_config(user_id)
        cutoff = date.today() - timedelta(days=config.period_days)

        buys = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_symbol == symbol,
                Transaction.type == "buy",
                Transaction.date >= cutoff,
            )
            .order_by(Transaction.date.asc())
            .all()
        )

        buy_count = len(buys)
        is_quarantined = buy_count >= config.threshold

        quarantine_ends_at = None
        if is_quarantined:
            nth_buy_date = buys[config.threshold - 1].date
            quarantine_ends_at = nth_buy_date + timedelta(days=config.period_days)

        return QuarantineStatus(
            asset_symbol=symbol,
            buy_count_in_period=buy_count,
            is_quarantined=is_quarantined,
            quarantine_ends_at=quarantine_ends_at,
        )

    def get_all_statuses(self, user_id: str) -> list[QuarantineStatus]:
        config = self._get_config(user_id)
        cutoff = date.today() - timedelta(days=config.period_days)

        symbols = (
            self.db.query(Transaction.asset_symbol)
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == "buy",
            )
            .distinct()
            .all()
        )

        return [
            self.get_asset_status(user_id, symbol[0])
            for symbol in symbols
        ]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_services/test_quarantine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add quarantine service with configurable threshold and period"
```

---

### Task 9: Portfolio service

**Files:**
- Create: `backend/app/services/portfolio.py`
- Create: `backend/tests/test_services/test_portfolio.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_portfolio.py
from datetime import date
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.services.portfolio import PortfolioService


def _setup_portfolio(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=100.0)
    db.add(ac)
    db.commit()

    aw1 = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=60.0)
    aw2 = AssetWeight(asset_class_id=ac.id, symbol="MSFT", target_weight=40.0)
    db.add_all([aw1, aw2])
    db.commit()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=150, total_value=1500,
        currency="USD", tax_amount=0, date=date(2026, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="MSFT",
        type="buy", quantity=5, unit_price=400, total_value=2000,
        currency="USD", tax_amount=0, date=date(2026, 1, 1),
    ))
    db.commit()
    return user


def test_get_holdings(db):
    user = _setup_portfolio(db)
    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)

    assert len(holdings) == 2
    aapl = next(h for h in holdings if h["symbol"] == "AAPL")
    assert aapl["quantity"] == 10
    assert aapl["avg_price"] == 150.0


def test_get_holdings_with_sells(db):
    user = _setup_portfolio(db)

    db.add(Transaction(
        user_id=user.id, asset_class_id=db.query(AssetClass).first().id,
        asset_symbol="AAPL", type="sell", quantity=3, unit_price=160,
        total_value=480, currency="USD", tax_amount=0, date=date(2026, 2, 1),
    ))
    db.commit()

    service = PortfolioService(db)
    holdings = service.get_holdings(user.id)

    aapl = next(h for h in holdings if h["symbol"] == "AAPL")
    assert aapl["quantity"] == 7


def test_get_allocation(db):
    user = _setup_portfolio(db)
    service = PortfolioService(db)
    allocation = service.get_allocation(user.id)

    assert len(allocation) == 1
    us_stocks = allocation[0]
    assert us_stocks["class_name"] == "US Stocks"
    assert us_stocks["target_weight"] == 100.0
    assert len(us_stocks["assets"]) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_services/test_portfolio.py -v`
Expected: FAIL

**Step 3: Implement portfolio service**

```python
# backend/app/services/portfolio.py
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def get_holdings(self, user_id: str) -> list[dict]:
        buys = (
            self.db.query(
                Transaction.asset_symbol,
                Transaction.asset_class_id,
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.total_value).label("total_cost"),
            )
            .filter(Transaction.user_id == user_id, Transaction.type == "buy")
            .group_by(Transaction.asset_symbol, Transaction.asset_class_id)
            .all()
        )

        sells = (
            self.db.query(
                Transaction.asset_symbol,
                func.sum(Transaction.quantity).label("total_qty"),
            )
            .filter(Transaction.user_id == user_id, Transaction.type == "sell")
            .group_by(Transaction.asset_symbol)
            .all()
        )
        sell_map = {s.asset_symbol: s.total_qty for s in sells}

        holdings = []
        for buy in buys:
            sold_qty = sell_map.get(buy.asset_symbol, 0)
            net_qty = buy.total_qty - sold_qty
            if net_qty <= 0:
                continue
            avg_price = buy.total_cost / buy.total_qty if buy.total_qty > 0 else 0
            holdings.append({
                "symbol": buy.asset_symbol,
                "asset_class_id": buy.asset_class_id,
                "quantity": net_qty,
                "avg_price": avg_price,
                "total_cost": avg_price * net_qty,
            })
        return holdings

    def get_allocation(self, user_id: str) -> list[dict]:
        classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id)
            .all()
        )

        holdings = self.get_holdings(user_id)
        holdings_by_class = {}
        for h in holdings:
            holdings_by_class.setdefault(h["asset_class_id"], []).append(h)

        result = []
        for ac in classes:
            class_holdings = holdings_by_class.get(ac.id, [])
            assets = []
            for h in class_holdings:
                aw = (
                    self.db.query(AssetWeight)
                    .filter_by(asset_class_id=ac.id, symbol=h["symbol"])
                    .first()
                )
                assets.append({
                    "symbol": h["symbol"],
                    "quantity": h["quantity"],
                    "total_cost": h["total_cost"],
                    "target_weight": aw.target_weight if aw else 0.0,
                })

            result.append({
                "class_id": ac.id,
                "class_name": ac.name,
                "target_weight": ac.target_weight,
                "assets": assets,
            })
        return result
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_services/test_portfolio.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add portfolio service with holdings and allocation"
```

---

### Task 10: Recommendation service

**Files:**
- Create: `backend/app/services/recommendation.py`
- Create: `backend/tests/test_services/test_recommendation.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_services/test_recommendation.py
from datetime import date
from unittest.mock import patch

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.models.quarantine_config import QuarantineConfig
from app.services.recommendation import RecommendationService


def _setup(db):
    user = User(name="Test", email="test@example.com")
    db.add(user)
    db.commit()

    qc = QuarantineConfig(user_id=user.id)
    db.add(qc)
    db.commit()

    us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0)
    crypto = AssetClass(user_id=user.id, name="Crypto", target_weight=50.0)
    db.add_all([us, crypto])
    db.commit()

    db.add_all([
        AssetWeight(asset_class_id=us.id, symbol="AAPL", target_weight=50.0),
        AssetWeight(asset_class_id=us.id, symbol="MSFT", target_weight=50.0),
        AssetWeight(asset_class_id=crypto.id, symbol="BTC", target_weight=100.0),
    ])
    db.commit()

    # AAPL overweight, MSFT on target, BTC underweight
    db.add(Transaction(
        user_id=user.id, asset_class_id=us.id, asset_symbol="AAPL",
        type="buy", quantity=20, unit_price=150, total_value=3000,
        currency="USD", tax_amount=0, date=date(2026, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=us.id, asset_symbol="MSFT",
        type="buy", quantity=5, unit_price=400, total_value=2000,
        currency="USD", tax_amount=0, date=date(2026, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=crypto.id, asset_symbol="BTC",
        type="buy", quantity=0.01, unit_price=65000, total_value=650,
        currency="USD", tax_amount=0, date=date(2026, 1, 1),
    ))
    db.commit()
    return user


@patch("app.services.recommendation.MarketDataService")
def test_recommend_top_2(mock_mds_cls, db):
    mock_mds = mock_mds_cls.return_value
    mock_mds.get_stock_quote.side_effect = lambda s: {
        "AAPL": {"current_price": 150.0},
        "MSFT": {"current_price": 400.0},
    }[s]
    mock_mds.get_crypto_quote.return_value = {"current_price": 65000.0}

    user = _setup(db)
    service = RecommendationService(db)
    recs = service.get_recommendations(user.id, count=2)

    assert len(recs) == 2
    # BTC is most underweight (effective target 50%, actual ~11.5%)
    assert recs[0]["symbol"] == "BTC"


@patch("app.services.recommendation.MarketDataService")
def test_quarantined_asset_excluded(mock_mds_cls, db):
    mock_mds = mock_mds_cls.return_value
    mock_mds.get_stock_quote.side_effect = lambda s: {
        "AAPL": {"current_price": 150.0},
        "MSFT": {"current_price": 400.0},
    }[s]
    mock_mds.get_crypto_quote.return_value = {"current_price": 65000.0}

    user = _setup(db)

    # Add second BTC buy to trigger quarantine
    crypto = db.query(AssetClass).filter_by(name="Crypto").first()
    db.add(Transaction(
        user_id=user.id, asset_class_id=crypto.id, asset_symbol="BTC",
        type="buy", quantity=0.01, unit_price=65000, total_value=650,
        currency="USD", tax_amount=0, date=date(2026, 3, 1),
    ))
    db.commit()

    service = RecommendationService(db)
    recs = service.get_recommendations(user.id, count=2)

    symbols = [r["symbol"] for r in recs]
    assert "BTC" not in symbols
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_services/test_recommendation.py -v`
Expected: FAIL

**Step 3: Implement recommendation service**

```python
# backend/app/services/recommendation.py
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService
from app.services.quarantine import QuarantineService

# CoinGecko symbol mapping
CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin",
    "BTC-USD": "bitcoin",
    "ETH": "ethereum",
    "ETH-USD": "ethereum",
    "USDT": "tether",
    "USDT-USD": "tether",
    "USDC": "usd-coin",
    "USDC-USD": "usd-coin",
    "DAI": "dai",
    "DAI-USD": "dai",
}

CRYPTO_CLASS_NAMES = {"Crypto", "Stablecoins"}


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.market = MarketDataService()
        self.portfolio = PortfolioService(db)
        self.quarantine = QuarantineService(db)

    def _get_current_price(self, symbol: str, class_name: str) -> float:
        if class_name in CRYPTO_CLASS_NAMES:
            coin_id = CRYPTO_COINGECKO_MAP.get(symbol, symbol.lower())
            quote = self.market.get_crypto_quote(coin_id)
        else:
            quote = self.market.get_stock_quote(symbol)
        return quote.get("current_price", 0.0)

    def get_recommendations(self, user_id: str, count: int = 2) -> list[dict]:
        classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id)
            .all()
        )

        holdings = self.portfolio.get_holdings(user_id)
        holdings_map = {h["symbol"]: h for h in holdings}

        # Calculate total portfolio value at current prices
        total_value = 0.0
        asset_values = {}
        all_assets = []

        for ac in classes:
            assets = (
                self.db.query(AssetWeight)
                .filter(AssetWeight.asset_class_id == ac.id)
                .all()
            )
            for aw in assets:
                holding = holdings_map.get(aw.symbol)
                if holding:
                    price = self._get_current_price(aw.symbol, ac.name)
                    value = holding["quantity"] * price
                else:
                    value = 0.0
                asset_values[aw.symbol] = value
                total_value += value
                all_assets.append({
                    "symbol": aw.symbol,
                    "class_name": ac.name,
                    "class_weight": ac.target_weight,
                    "asset_weight": aw.target_weight,
                })

        if total_value == 0:
            return [
                {"symbol": a["symbol"], "class_name": a["class_name"],
                 "effective_target": a["class_weight"] * a["asset_weight"] / 100,
                 "actual_weight": 0.0,
                 "diff": a["class_weight"] * a["asset_weight"] / 100}
                for a in all_assets[:count]
            ]

        # Get quarantine statuses
        quarantine_statuses = self.quarantine.get_all_statuses(user_id)
        quarantined = {s.asset_symbol for s in quarantine_statuses if s.is_quarantined}

        # Calculate diffs
        diffs = []
        for asset in all_assets:
            symbol = asset["symbol"]
            if symbol in quarantined:
                continue
            effective_target = asset["class_weight"] * asset["asset_weight"] / 100.0
            actual_weight = (asset_values.get(symbol, 0) / total_value) * 100.0
            diff = effective_target - actual_weight

            diffs.append({
                "symbol": symbol,
                "class_name": asset["class_name"],
                "effective_target": round(effective_target, 2),
                "actual_weight": round(actual_weight, 2),
                "diff": round(diff, 2),
            })

        diffs.sort(key=lambda d: d["diff"], reverse=True)
        return diffs[:count]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_services/test_recommendation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/ backend/tests/test_services/
git commit -m "feat: add recommendation service with quarantine exclusion"
```

---

## Phase 3: Backend API Routers

### Task 11: Rate limiting middleware

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/rate_limit.py`
- Modify: `backend/app/main.py`

**Step 1: Implement rate limiting**

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

MARKET_DATA_LIMIT = "30/minute"
CRUD_LIMIT = "60/minute"
```

**Step 2: Add to main.py**

Add to `backend/app/main.py`:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.middleware.rate_limit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Step 3: Commit**

```bash
git add backend/app/middleware/ backend/app/main.py
git commit -m "feat: add rate limiting middleware with slowapi"
```

---

### Task 12: Asset classes router

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/asset_classes.py`
- Create: `backend/tests/test_routers/__init__.py`
- Create: `backend/tests/test_routers/test_asset_classes.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

**Step 1: Add default user fixture to conftest.py**

Add to `backend/tests/conftest.py`:
```python
from app.models.user import User

@pytest.fixture
def default_user(db):
    user = User(name="Default User", email="default@example.com")
    db.add(user)
    db.commit()
    return user
```

**Step 2: Write the failing test**

```python
# backend/tests/test_routers/test_asset_classes.py

def test_create_asset_class(client, default_user):
    response = client.post("/api/asset-classes", json={
        "name": "US Stocks",
        "target_weight": 40.0,
    }, headers={"X-User-Id": default_user.id})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "US Stocks"
    assert data["target_weight"] == 40.0


def test_list_asset_classes(client, default_user):
    client.post("/api/asset-classes", json={"name": "US Stocks", "target_weight": 50.0},
                headers={"X-User-Id": default_user.id})
    client.post("/api/asset-classes", json={"name": "Crypto", "target_weight": 50.0},
                headers={"X-User-Id": default_user.id})

    response = client.get("/api/asset-classes", headers={"X-User-Id": default_user.id})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_asset_class(client, default_user):
    create = client.post("/api/asset-classes", json={"name": "US Stocks", "target_weight": 40.0},
                         headers={"X-User-Id": default_user.id})
    ac_id = create.json()["id"]

    response = client.put(f"/api/asset-classes/{ac_id}", json={"target_weight": 60.0},
                          headers={"X-User-Id": default_user.id})
    assert response.status_code == 200
    assert response.json()["target_weight"] == 60.0


def test_delete_asset_class(client, default_user):
    create = client.post("/api/asset-classes", json={"name": "US Stocks"},
                         headers={"X-User-Id": default_user.id})
    ac_id = create.json()["id"]

    response = client.delete(f"/api/asset-classes/{ac_id}", headers={"X-User-Id": default_user.id})
    assert response.status_code == 204

    response = client.get("/api/asset-classes", headers={"X-User-Id": default_user.id})
    assert len(response.json()) == 0
```

**Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routers/test_asset_classes.py -v`
Expected: FAIL

**Step 4: Implement router**

Note: We use `X-User-Id` header for now (single-user). This becomes JWT/auth later.

```python
# backend/app/routers/asset_classes.py
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.schemas.asset_class import AssetClassCreate, AssetClassUpdate, AssetClassResponse

router = APIRouter(prefix="/api/asset-classes", tags=["asset-classes"])


@router.get("", response_model=list[AssetClassResponse])
@limiter.limit(CRUD_LIMIT)
def list_asset_classes(request, x_user_id: str = Header(), db: Session = Depends(get_db)):
    return db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()


@router.post("", response_model=AssetClassResponse, status_code=201)
@limiter.limit(CRUD_LIMIT)
def create_asset_class(request, body: AssetClassCreate, x_user_id: str = Header(), db: Session = Depends(get_db)):
    ac = AssetClass(user_id=x_user_id, name=body.name, target_weight=body.target_weight)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


@router.put("/{ac_id}", response_model=AssetClassResponse)
@limiter.limit(CRUD_LIMIT)
def update_asset_class(request, ac_id: str, body: AssetClassUpdate, x_user_id: str = Header(), db: Session = Depends(get_db)):
    ac = db.query(AssetClass).filter(AssetClass.id == ac_id, AssetClass.user_id == x_user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    if body.name is not None:
        ac.name = body.name
    if body.target_weight is not None:
        ac.target_weight = body.target_weight
    db.commit()
    db.refresh(ac)
    return ac


@router.delete("/{ac_id}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_asset_class(request, ac_id: str, x_user_id: str = Header(), db: Session = Depends(get_db)):
    ac = db.query(AssetClass).filter(AssetClass.id == ac_id, AssetClass.user_id == x_user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    db.delete(ac)
    db.commit()
```

Add to `backend/app/main.py`:
```python
from app.routers import asset_classes
app.include_router(asset_classes.router)
```

**Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_routers/test_asset_classes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add asset classes CRUD router"
```

---

### Task 13: Asset weights router

**Files:**
- Create: `backend/app/routers/asset_weights.py`
- Create: `backend/tests/test_routers/test_asset_weights.py`
- Modify: `backend/app/main.py`

Follow same pattern as Task 12. Router endpoints:
- `GET /api/asset-classes/{id}/assets`
- `POST /api/asset-classes/{id}/assets`
- `PUT /api/asset-weights/{id}`
- `DELETE /api/asset-weights/{id}`

**Commit:** `git commit -m "feat: add asset weights CRUD router"`

---

### Task 14: Transactions router

**Files:**
- Create: `backend/app/routers/transactions.py`
- Create: `backend/tests/test_routers/test_transactions.py`
- Modify: `backend/app/main.py`

Router endpoints:
- `GET /api/transactions` (filterable by type, symbol, date_from, date_to query params)
- `POST /api/transactions`
- `PUT /api/transactions/{id}`
- `DELETE /api/transactions/{id}`

**Commit:** `git commit -m "feat: add transactions CRUD router with filtering"`

---

### Task 15: Market data router

**Files:**
- Create: `backend/app/routers/stocks.py`
- Create: `backend/app/routers/crypto.py`
- Create: `backend/tests/test_routers/test_stocks.py`
- Create: `backend/tests/test_routers/test_crypto.py`
- Modify: `backend/app/main.py`

Router endpoints:
- `GET /api/stocks/{symbol}` (rate limit: 30/min)
- `GET /api/stocks/{symbol}/history?period=1mo`
- `GET /api/crypto/{symbol}` (rate limit: 30/min)
- `GET /api/crypto/{symbol}/history?days=30`

All tests mock MarketDataService.

**Commit:** `git commit -m "feat: add market data routers for stocks and crypto"`

---

### Task 16: Portfolio router

**Files:**
- Create: `backend/app/routers/portfolio.py`
- Create: `backend/tests/test_routers/test_portfolio.py`
- Modify: `backend/app/main.py`

Router endpoints:
- `GET /api/portfolio/summary`
- `GET /api/portfolio/performance`
- `GET /api/portfolio/allocation`

**Commit:** `git commit -m "feat: add portfolio router with summary, performance, allocation"`

---

### Task 17: Recommendations and quarantine routers

**Files:**
- Create: `backend/app/routers/recommendations.py`
- Create: `backend/app/routers/quarantine.py`
- Create: `backend/tests/test_routers/test_recommendations.py`
- Create: `backend/tests/test_routers/test_quarantine.py`
- Modify: `backend/app/main.py`

Router endpoints:
- `GET /api/recommendations?count=2`
- `GET /api/quarantine/status`
- `GET /api/quarantine/config`
- `PUT /api/quarantine/config`

**Commit:** `git commit -m "feat: add recommendations and quarantine routers"`

---

## Phase 4: Frontend Foundation

### Task 18: Frontend scaffolding

**Step 1: Create React app with Vite**

```bash
cd /Users/felipediaspereira/Code/project-fin
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom axios recharts tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

**Step 2: Configure Vite**

Update `frontend/vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
```

**Step 3: Create test setup**

```typescript
// frontend/src/test/setup.ts
import "@testing-library/jest-dom";
```

**Step 4: Create API client**

```typescript
// frontend/src/services/api.ts
import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: {
    "X-User-Id": "default-user-id",
  },
});

export default api;
```

**Step 5: Create types**

```typescript
// frontend/src/types/index.ts
export interface AssetClass {
  id: string;
  user_id: string;
  name: string;
  target_weight: number;
  created_at: string;
  updated_at: string;
}

export interface AssetWeight {
  id: string;
  asset_class_id: string;
  symbol: string;
  target_weight: number;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  asset_class_id: string;
  asset_symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number;
  unit_price: number;
  total_value: number;
  currency: "BRL" | "USD";
  tax_amount: number;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number;
  avg_price: number;
  total_cost: number;
  current_price?: number;
  current_value?: number;
  gain_loss?: number;
  target_weight?: number;
  actual_weight?: number;
}

export interface Recommendation {
  symbol: string;
  class_name: string;
  effective_target: number;
  actual_weight: number;
  diff: number;
}

export interface QuarantineStatus {
  asset_symbol: string;
  buy_count_in_period: number;
  is_quarantined: boolean;
  quarantine_ends_at: string | null;
}

export interface QuarantineConfig {
  id: string;
  user_id: string;
  threshold: number;
  period_days: number;
}
```

**Step 6: Set up routing**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Settings from "./pages/Settings";
import Market from "./pages/Market";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/market" element={<Market />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

**Step 7: Create placeholder pages and Navbar**

Create stub components for `Navbar`, `Dashboard`, `Portfolio`, `Settings`, `Market` that render a heading.

**Step 8: Verify**

Run: `cd frontend && npm run dev` — should show app with nav and routing.

**Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with routing, types, API client"
```

---

## Phase 5: Frontend Components

### Task 19: Shared components (DataTable, ChartCard, QuarantineBadge)

**Files:**
- Create: `frontend/src/components/DataTable.tsx`
- Create: `frontend/src/components/ChartCard.tsx`
- Create: `frontend/src/components/QuarantineBadge.tsx`
- Create: `frontend/src/components/__tests__/DataTable.test.tsx`
- Create: `frontend/src/components/__tests__/QuarantineBadge.test.tsx`

DataTable: reusable sortable/filterable table with inline editing support.
ChartCard: wrapper div with title for Recharts charts.
QuarantineBadge: visual indicator (yellow/orange badge with icon) for quarantined assets.

TDD: write component tests first, then implement.

**Commit:** `git commit -m "feat: add shared components DataTable, ChartCard, QuarantineBadge"`

---

### Task 20: Portfolio page — Asset Classes table

**Files:**
- Create: `frontend/src/components/AssetClassesTable.tsx`
- Create: `frontend/src/hooks/useAssetClasses.ts`
- Create: `frontend/src/components/__tests__/AssetClassesTable.test.tsx`
- Modify: `frontend/src/pages/Portfolio.tsx`

Features: list classes, inline edit target weight, add/remove class.

**Commit:** `git commit -m "feat: add asset classes table with inline weight editing"`

---

### Task 21: Portfolio page — Holdings table

**Files:**
- Create: `frontend/src/components/HoldingsTable.tsx`
- Create: `frontend/src/components/TransactionForm.tsx`
- Create: `frontend/src/hooks/usePortfolio.ts`
- Create: `frontend/src/hooks/useTransactions.ts`
- Create: `frontend/src/components/__tests__/HoldingsTable.test.tsx`
- Modify: `frontend/src/pages/Portfolio.tsx`

Features: holdings per class, inline edit asset weight, buy/sell buttons, expandable row with transaction history, quarantine badges, add asset.

**Commit:** `git commit -m "feat: add holdings table with transactions and quarantine badges"`

---

### Task 22: Portfolio page — Dividends table and composition chart

**Files:**
- Create: `frontend/src/components/DividendsTable.tsx`
- Create: `frontend/src/components/PortfolioCompositionChart.tsx`
- Create: `frontend/src/components/__tests__/DividendsTable.test.tsx`
- Modify: `frontend/src/pages/Portfolio.tsx`

Dividends table: symbol, date, amount, currency, tax, notes, filterable, add button.
Composition chart: donut chart using Recharts PieChart.

**Commit:** `git commit -m "feat: add dividends table and portfolio composition donut chart"`

---

### Task 23: Dashboard page

**Files:**
- Create: `frontend/src/components/PerformanceChart.tsx`
- Create: `frontend/src/components/AllocationChart.tsx`
- Create: `frontend/src/components/RecommendationCard.tsx`
- Create: `frontend/src/hooks/useRecommendations.ts`
- Create: `frontend/src/components/__tests__/RecommendationCard.test.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`

Performance chart: Recharts LineChart of portfolio value over time.
Allocation chart: Recharts BarChart target vs actual.
Recommendation card: top N assets to invest with diff values.

**Commit:** `git commit -m "feat: add dashboard with performance, allocation charts and recommendations"`

---

### Task 24: Settings page

**Files:**
- Create: `frontend/src/hooks/useQuarantine.ts`
- Create: `frontend/src/components/__tests__/Settings.test.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

Settings: quarantine config (threshold + period inputs), recommendation count input.

**Commit:** `git commit -m "feat: add settings page for quarantine and recommendation config"`

---

### Task 25: Market page

**Files:**
- Create: `frontend/src/hooks/useMarketData.ts`
- Create: `frontend/src/components/MarketSearch.tsx`
- Modify: `frontend/src/pages/Market.tsx`

Search bar for stock/crypto tickers, shows price info and mini chart.

**Commit:** `git commit -m "feat: add market search page for stocks and crypto"`

---

## Phase 6: Integration and Deployment

### Task 26: Docker setup

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./project_fin.db
      - CORS_ORIGIN=http://localhost:3000
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

**Commit:** `git commit -m "feat: add Docker and docker-compose setup"`

---

### Task 27: Seed data and default user

**Files:**
- Create: `backend/app/seed.py`

Create a seed script that:
1. Creates default user
2. Creates default asset classes (US Stocks, BR Stocks, Crypto, Stablecoins) with equal weights
3. Creates default quarantine config

Run on first startup if DB is empty.

**Commit:** `git commit -m "feat: add seed data for default user and asset classes"`

---

### Task 28: End-to-end smoke test

**Files:**
- Create: `backend/tests/test_e2e.py`

Test the full flow:
1. Create asset classes
2. Add assets to classes
3. Record buy transactions
4. Get portfolio summary
5. Get recommendations
6. Verify quarantine triggers after 2 buys

Run: `cd backend && pytest tests/test_e2e.py -v`

**Commit:** `git commit -m "test: add end-to-end smoke test for full investment flow"`

---

## Summary

| Phase | Tasks | Description |
|---|---|---|
| 1 | 1-6 | Backend foundation: scaffolding + all models |
| 2 | 7-10 | Backend services: market data, quarantine, portfolio, recommendations |
| 3 | 11-17 | Backend API routers with rate limiting |
| 4 | 18 | Frontend scaffolding |
| 5 | 19-25 | Frontend components and pages |
| 6 | 26-28 | Docker, seed data, E2E test |

Total: 28 tasks

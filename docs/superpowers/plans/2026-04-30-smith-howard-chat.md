# Smith+Howard Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an enterprise AI chat gateway branded as Smith+Howard Chat — FastAPI backend proxying to Claude API with content filtering, React frontend with streaming chat UI, Docker Compose deployment with mock SSO auth.

**Architecture:** Three containers (Nginx, FastAPI, React SPA) orchestrated via Docker Compose. No database. FastAPI validates JWT tokens, runs content filtering on messages/files, and streams Claude API responses via SSE. React stores conversations in browser sessionStorage only.

**Tech Stack:** Python 3.12 / FastAPI / uvicorn, React 18 / TypeScript / Vite, Nginx, Docker Compose, Anthropic Python SDK, PyJWT, PyYAML, openpyxl, react-markdown

---

## File Map

```
chatgateway/
├── docker-compose.yml              # Orchestrates nginx, backend, frontend-build
├── .env.example                    # Template environment variables
├── .gitignore                      # Standard Python + Node + Docker ignores
├── config/
│   └── content-filter.yaml         # Content filter rules (YAML)
├── backend/
│   ├── Dockerfile                  # Python 3.12 slim image
│   ├── requirements.txt            # Python dependencies
│   ├── main.py                     # FastAPI app entry + CORS + lifespan
│   ├── config.py                   # Settings via pydantic-settings
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── provider.py             # AuthProvider protocol + get_provider factory
│   │   ├── mock_provider.py        # Mock IdP: issue JWTs, list users
│   │   └── middleware.py           # JWT validation dependency
│   ├── filter/
│   │   ├── __init__.py
│   │   ├── engine.py               # ContentFilter class: scan text
│   │   ├── rules.py                # Load rules from YAML
│   │   ├── luhn.py                 # Luhn algorithm for card detection
│   │   └── scanners.py            # Extract text from CSV/Excel files
│   ├── proxy/
│   │   ├── __init__.py
│   │   └── claude.py               # Claude API streaming proxy
│   └── routes/
│       ├── __init__.py
│       ├── auth.py                 # /api/auth/* routes
│       ├── chat.py                 # /api/chat route
│       ├── files.py                # /api/files/upload route
│       └── health.py               # /api/health route
├── backend/tests/
│   ├── conftest.py                 # Shared fixtures
│   ├── test_auth.py                # Auth endpoint + middleware tests
│   ├── test_filter.py              # Content filter tests
│   ├── test_luhn.py                # Luhn algorithm tests
│   ├── test_scanners.py            # File scanner tests
│   ├── test_chat.py                # Chat endpoint tests (mocked Claude)
│   └── test_files.py               # File upload tests
├── frontend/
│   ├── Dockerfile                  # Multi-stage: build + nginx serve
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx                # React entry
│       ├── App.tsx                 # Router: login vs chat
│       ├── types.ts                # Shared TypeScript types
│       ├── components/
│       │   ├── Header.tsx          # S+H branded header bar
│       │   ├── LoginPage.tsx       # Mock login user picker
│       │   ├── ChatWindow.tsx      # Main chat container
│       │   ├── MessageBubble.tsx   # Message rendering (markdown)
│       │   ├── InputBar.tsx        # Text input + file attach + send
│       │   └── FilterToast.tsx     # Content filter warning toast
│       ├── hooks/
│       │   ├── useAuth.ts          # Auth token management
│       │   └── useChat.ts          # Chat state + streaming + sessionStorage
│       └── services/
│           └── api.ts              # API client (fetch, SSE, file upload)
├── nginx/
│   └── nginx.conf                  # Reverse proxy config
└── docs/
    └── production-guide.md         # PoC-to-production steps
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config/content-filter.yaml`
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env
.env.local

# Docker
docker-compose.override.yml

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Superpowers
.superpowers/
```

- [ ] **Step 2: Create .env.example**

```env
# Auth
AUTH_PROVIDER=mock
MOCK_USERS=john.doe,jane.smith,admin
JWT_SECRET=local-dev-secret-change-me

# Claude API
ANTHROPIC_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-20250514

# Server
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

- [ ] **Step 3: Create config/content-filter.yaml**

```yaml
rules:
  - name: uk_national_insurance
    pattern: '[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]'
    action: block
    message: "Message blocked: contains what appears to be a National Insurance number"

  - name: credit_card
    type: luhn
    min_digits: 13
    max_digits: 19
    action: block
    message: "Message blocked: contains what appears to be a credit/debit card number"

  - name: uk_bank_account
    pattern: '\d{2}-\d{2}-\d{2}\s*\d{8}'
    action: block
    message: "Message blocked: contains what appears to be a UK bank account number"

  - name: email_address
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    action: warn
    message: "Warning: your message contains an email address"

allowed_file_types:
  - .csv
  - .xlsx
  - .pdf
  - .txt
  - .png
  - .jpg
```

- [ ] **Step 4: Create backend/requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic-settings==2.5.0
pyjwt==2.9.0
pyyaml==6.0.2
anthropic==0.39.0
python-multipart==0.0.12
openpyxl==3.1.5
httpx==0.27.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 5: Create backend/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    auth_provider: str = "mock"
    mock_users: str = "john.doe,jane.smith,admin"
    jwt_secret: str = "local-dev-secret-change-me"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    content_filter_path: str = "config/content-filter.yaml"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 6: Create frontend/package.json**

```json
{
  "name": "smith-howard-chat",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "rehype-highlight": "^7.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0"
  }
}
```

- [ ] **Step 7: Create frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

- [ ] **Step 8: Create frontend/vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 9: Create frontend/index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Smith+Howard Chat</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 10: Commit**

```bash
git add .gitignore .env.example config/ backend/requirements.txt backend/config.py frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html
git commit -m "feat: project scaffolding with config and dependencies"
```

---

## Task 2: Backend — Content Filter Engine

**Files:**
- Create: `backend/filter/__init__.py`
- Create: `backend/filter/luhn.py`
- Create: `backend/filter/rules.py`
- Create: `backend/filter/engine.py`
- Create: `backend/filter/scanners.py`
- Test: `backend/tests/test_luhn.py`
- Test: `backend/tests/test_filter.py`
- Test: `backend/tests/test_scanners.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create backend/filter/__init__.py and backend/tests/__init__.py**

```python
# backend/filter/__init__.py
# backend/tests/__init__.py
```

Both empty `__init__.py` files.

- [ ] **Step 2: Create conftest.py with shared fixtures**

```python
# backend/tests/conftest.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
```

- [ ] **Step 3: Write failing test for Luhn algorithm**

```python
# backend/tests/test_luhn.py
from filter.luhn import is_luhn_valid, find_card_numbers


def test_valid_card_number():
    assert is_luhn_valid("4111111111111111") is True


def test_invalid_card_number():
    assert is_luhn_valid("4111111111111112") is False


def test_find_card_in_text():
    text = "My card is 4111111111111111 please charge it"
    results = find_card_numbers(text)
    assert len(results) == 1
    assert results[0] == "4111111111111111"


def test_no_card_in_text():
    text = "This is a normal message about quarterly revenue of 1234567890123"
    results = find_card_numbers(text)
    assert len(results) == 0


def test_multiple_cards():
    text = "Cards: 4111111111111111 and 5500000000000004"
    results = find_card_numbers(text)
    assert len(results) == 2
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_luhn.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'filter.luhn'`

- [ ] **Step 5: Implement Luhn algorithm**

```python
# backend/filter/luhn.py
import re


def is_luhn_valid(number_str: str) -> bool:
    digits = [int(d) for d in number_str]
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_card_numbers(text: str, min_digits: int = 13, max_digits: int = 19) -> list[str]:
    pattern = rf'\b(\d{{{min_digits},{max_digits}}})\b'
    candidates = re.findall(pattern, text)
    return [c for c in candidates if is_luhn_valid(c)]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_luhn.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Write failing test for rules loader**

```python
# backend/tests/test_filter.py
import os
from filter.rules import load_rules
from filter.engine import ContentFilter, FilterResult


FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "content-filter.yaml")


def test_load_rules_from_yaml():
    rules = load_rules(FIXTURE_PATH)
    assert len(rules.rules) >= 4
    assert rules.allowed_file_types == [".csv", ".xlsx", ".pdf", ".txt", ".png", ".jpg"]


def test_filter_blocks_ni_number():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("My NI number is AB123456C")
    assert result.blocked is True
    assert result.rule == "uk_national_insurance"


def test_filter_blocks_credit_card():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Pay with 4111111111111111 please")
    assert result.blocked is True
    assert result.rule == "credit_card"


def test_filter_blocks_bank_account():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Sort code 12-34-56 account 12345678")
    assert result.blocked is True
    assert result.rule == "uk_bank_account"


def test_filter_warns_email():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("Contact john@example.com for details")
    assert result.blocked is False
    assert result.warned is True
    assert result.rule == "email_address"


def test_filter_passes_clean_text():
    f = ContentFilter(FIXTURE_PATH)
    result = f.scan_text("What is the quarterly revenue trend?")
    assert result.blocked is False
    assert result.warned is False


def test_filter_checks_file_type_allowed():
    f = ContentFilter(FIXTURE_PATH)
    assert f.is_file_type_allowed(".csv") is True
    assert f.is_file_type_allowed(".exe") is False
```

- [ ] **Step 8: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_filter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'filter.rules'`

- [ ] **Step 9: Implement rules loader**

```python
# backend/filter/rules.py
from dataclasses import dataclass, field
import yaml


@dataclass
class Rule:
    name: str
    action: str
    message: str
    pattern: str | None = None
    type: str | None = None
    min_digits: int = 13
    max_digits: int = 19


@dataclass
class FilterConfig:
    rules: list[Rule] = field(default_factory=list)
    allowed_file_types: list[str] = field(default_factory=list)


def load_rules(path: str) -> FilterConfig:
    with open(path) as f:
        data = yaml.safe_load(f)

    rules = []
    for r in data.get("rules", []):
        rules.append(Rule(
            name=r["name"],
            action=r["action"],
            message=r["message"],
            pattern=r.get("pattern"),
            type=r.get("type"),
            min_digits=r.get("min_digits", 13),
            max_digits=r.get("max_digits", 19),
        ))

    return FilterConfig(
        rules=rules,
        allowed_file_types=data.get("allowed_file_types", []),
    )
```

- [ ] **Step 10: Implement content filter engine**

```python
# backend/filter/engine.py
import re
from dataclasses import dataclass
from filter.rules import load_rules, FilterConfig
from filter.luhn import find_card_numbers


@dataclass
class FilterResult:
    blocked: bool = False
    warned: bool = False
    rule: str | None = None
    message: str | None = None


class ContentFilter:
    def __init__(self, config_path: str):
        self.config: FilterConfig = load_rules(config_path)

    def scan_text(self, text: str) -> FilterResult:
        for rule in self.config.rules:
            if rule.type == "luhn":
                matches = find_card_numbers(text, rule.min_digits, rule.max_digits)
                if matches:
                    if rule.action == "block":
                        return FilterResult(blocked=True, rule=rule.name, message=rule.message)
                    else:
                        return FilterResult(warned=True, rule=rule.name, message=rule.message)
            elif rule.pattern:
                if re.search(rule.pattern, text):
                    if rule.action == "block":
                        return FilterResult(blocked=True, rule=rule.name, message=rule.message)
                    else:
                        return FilterResult(warned=True, rule=rule.name, message=rule.message)

        return FilterResult()

    def is_file_type_allowed(self, extension: str) -> bool:
        return extension.lower() in self.config.allowed_file_types
```

- [ ] **Step 11: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_filter.py tests/test_luhn.py -v`
Expected: All tests PASS

- [ ] **Step 12: Write failing test for file scanners**

```python
# backend/tests/test_scanners.py
import io
import csv
from filter.scanners import extract_text_from_csv, extract_text_from_xlsx


def test_extract_text_from_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "NI Number", "Amount"])
    writer.writerow(["John Doe", "AB123456C", "5000"])
    content = output.getvalue().encode()
    text = extract_text_from_csv(content)
    assert "AB123456C" in text
    assert "John Doe" in text


def test_extract_text_from_xlsx(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Client", "Account"])
    ws.append(["Acme Corp", "12-34-56 12345678"])
    path = tmp_path / "test.xlsx"
    wb.save(path)
    with open(path, "rb") as f:
        content = f.read()
    text = extract_text_from_xlsx(content)
    assert "12-34-56 12345678" in text
    assert "Acme Corp" in text
```

- [ ] **Step 13: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_scanners.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'filter.scanners'`

- [ ] **Step 14: Implement file scanners**

```python
# backend/filter/scanners.py
import csv
import io
from openpyxl import load_workbook


def extract_text_from_csv(content: bytes) -> str:
    text_parts = []
    decoded = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(decoded))
    for row in reader:
        text_parts.extend(row)
    return " ".join(text_parts)


def extract_text_from_xlsx(content: bytes) -> str:
    text_parts = []
    wb = load_workbook(filename=io.BytesIO(content), read_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell is not None:
                    text_parts.append(str(cell))
    wb.close()
    return " ".join(text_parts)
```

- [ ] **Step 15: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_scanners.py -v`
Expected: All tests PASS

- [ ] **Step 16: Commit**

```bash
git add backend/filter/ backend/tests/
git commit -m "feat: content filter engine with Luhn, regex rules, and file scanners"
```

---

## Task 3: Backend — Authentication (Mock Provider)

**Files:**
- Create: `backend/auth/__init__.py`
- Create: `backend/auth/provider.py`
- Create: `backend/auth/mock_provider.py`
- Create: `backend/auth/middleware.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Create backend/auth/__init__.py**

Empty file.

- [ ] **Step 2: Write failing auth tests**

```python
# backend/tests/test_auth.py
import jwt
from auth.mock_provider import MockAuthProvider
from auth.middleware import decode_token


SECRET = "test-secret"


def test_mock_provider_lists_users():
    provider = MockAuthProvider(users="alice,bob,charlie", secret=SECRET)
    assert provider.list_users() == ["alice", "bob", "charlie"]


def test_mock_provider_creates_valid_jwt():
    provider = MockAuthProvider(users="alice,bob", secret=SECRET)
    token = provider.login("alice")
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload["email"] == "alice@smithhoward.com"
    assert payload["name"] == "alice"
    assert payload["roles"] == ["user"]
    assert "sub" in payload
    assert "exp" in payload


def test_mock_provider_rejects_unknown_user():
    provider = MockAuthProvider(users="alice,bob", secret=SECRET)
    token = provider.login("hacker")
    assert token is None


def test_decode_token_valid():
    provider = MockAuthProvider(users="alice", secret=SECRET)
    token = provider.login("alice")
    payload = decode_token(token, SECRET)
    assert payload["email"] == "alice@smithhoward.com"


def test_decode_token_invalid():
    payload = decode_token("invalid.token.here", SECRET)
    assert payload is None


def test_decode_token_expired():
    import time
    provider = MockAuthProvider(users="alice", secret=SECRET, token_expiry=-1)
    token = provider.login("alice")
    time.sleep(0.1)
    payload = decode_token(token, SECRET)
    assert payload is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.mock_provider'`

- [ ] **Step 4: Implement auth provider protocol**

```python
# backend/auth/provider.py
from typing import Protocol


class AuthProvider(Protocol):
    def login(self, username: str) -> str | None: ...
    def list_users(self) -> list[str]: ...
```

- [ ] **Step 5: Implement mock auth provider**

```python
# backend/auth/mock_provider.py
import uuid
import time
import jwt
from auth.provider import AuthProvider


class MockAuthProvider:
    def __init__(self, users: str, secret: str, token_expiry: int = 86400):
        self._users = [u.strip() for u in users.split(",")]
        self._secret = secret
        self._token_expiry = token_expiry

    def list_users(self) -> list[str]:
        return self._users

    def login(self, username: str) -> str | None:
        if username not in self._users:
            return None

        now = int(time.time())
        payload = {
            "sub": str(uuid.uuid5(uuid.NAMESPACE_DNS, username)),
            "email": f"{username}@smithhoward.com",
            "name": username,
            "roles": ["user"],
            "iat": now,
            "exp": now + self._token_expiry,
            "iss": "mock-idp",
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
```

- [ ] **Step 6: Implement token decode middleware**

```python
# backend/auth/middleware.py
import jwt


def decode_token(token: str, secret: str) -> dict | None:
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: All 6 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/auth/
git commit -m "feat: mock auth provider with JWT issuance and validation"
```

---

## Task 4: Backend — FastAPI App + Routes

**Files:**
- Create: `backend/main.py`
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/health.py`
- Create: `backend/routes/auth.py`
- Create: `backend/routes/chat.py`
- Create: `backend/routes/files.py`
- Create: `backend/proxy/__init__.py`
- Create: `backend/proxy/claude.py`
- Test: `backend/tests/test_chat.py`
- Test: `backend/tests/test_files.py`

- [ ] **Step 1: Create backend/routes/__init__.py and backend/proxy/__init__.py**

Both empty files.

- [ ] **Step 2: Implement health route**

```python
# backend/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Implement auth routes**

```python
# backend/routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import settings
from auth.mock_provider import MockAuthProvider

router = APIRouter(prefix="/api/auth")

_provider = MockAuthProvider(users=settings.mock_users, secret=settings.jwt_secret)


class LoginRequest(BaseModel):
    username: str


@router.get("/users")
async def list_users():
    return {"users": _provider.list_users()}


@router.post("/login")
async def login(body: LoginRequest):
    token = _provider.login(body.username)
    if token is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return {"token": token}
```

- [ ] **Step 4: Implement Claude streaming proxy**

```python
# backend/proxy/claude.py
from collections.abc import AsyncGenerator
import anthropic
from config import settings


async def stream_chat(messages: list[dict], model: str | None = None) -> AsyncGenerator[str, None]:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = model or settings.claude_model

    claude_messages = []
    for msg in messages:
        content = []
        if msg.get("content"):
            content.append({"type": "text", "text": msg["content"]})
        if msg.get("file_content"):
            content.append({"type": "text", "text": f"[File: {msg['file_name']}]\n{msg['file_content']}"})
        claude_messages.append({"role": msg["role"], "content": content})

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        messages=claude_messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
```

- [ ] **Step 5: Implement chat route**

```python
# backend/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from auth.middleware import decode_token
from filter.engine import ContentFilter
from proxy.claude import stream_chat
from config import settings

router = APIRouter(prefix="/api")

_filter = ContentFilter(settings.content_filter_path)


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header[7:]
    payload = decode_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


class ChatMessage(BaseModel):
    role: str
    content: str
    file_content: str | None = None
    file_name: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None


@router.post("/chat")
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    last_message = body.messages[-1]
    if last_message.role == "user":
        result = _filter.scan_text(last_message.content)
        if result.blocked:
            raise HTTPException(status_code=403, detail={
                "error": "content_filtered",
                "message": result.message,
                "rule": result.rule,
            })
        if last_message.file_content:
            file_result = _filter.scan_text(last_message.file_content)
            if file_result.blocked:
                raise HTTPException(status_code=403, detail={
                    "error": "content_filtered",
                    "message": file_result.message,
                    "rule": file_result.rule,
                })

    messages_dicts = [m.model_dump() for m in body.messages]

    async def event_stream():
        async for chunk in stream_chat(messages_dicts, body.model):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 6: Implement file upload route**

```python
# backend/routes/files.py
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from routes.chat import get_current_user
from filter.engine import ContentFilter
from filter.scanners import extract_text_from_csv, extract_text_from_xlsx
from config import settings

router = APIRouter(prefix="/api/files")

_filter = ContentFilter(settings.content_filter_path)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()

    if not _filter.is_file_type_allowed(ext):
        raise HTTPException(status_code=400, detail={
            "error": "file_type_not_allowed",
            "message": f"File type '{ext}' is not allowed. Allowed: {_filter.config.allowed_file_types}",
        })

    content = await file.read()

    extracted_text = ""
    if ext == ".csv":
        extracted_text = extract_text_from_csv(content)
    elif ext == ".xlsx":
        extracted_text = extract_text_from_xlsx(content)
    elif ext in (".txt", ".pdf"):
        extracted_text = content.decode("utf-8", errors="replace")

    if extracted_text:
        result = _filter.scan_text(extracted_text)
        if result.blocked:
            raise HTTPException(status_code=403, detail={
                "error": "content_filtered",
                "message": result.message,
                "rule": result.rule,
            })

    return {
        "file_name": file.filename,
        "file_content": extracted_text,
        "size": len(content),
    }
```

- [ ] **Step 7: Create FastAPI main app**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.files import router as files_router

app = FastAPI(title="Smith+Howard Chat Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(files_router)
```

- [ ] **Step 8: Write integration tests for chat endpoint**

```python
# backend/tests/test_chat.py
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app
from auth.mock_provider import MockAuthProvider

client = TestClient(app)
_provider = MockAuthProvider(users="testuser", secret="local-dev-secret-change-me")


def _auth_header():
    token = _provider.login("testuser")
    return {"Authorization": f"Bearer {token}"}


def test_chat_requires_auth():
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 401


def test_chat_blocks_ni_number():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "My NI is AB123456C"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "uk_national_insurance"


def test_chat_blocks_credit_card():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Card 4111111111111111"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "credit_card"


@patch("routes.chat.stream_chat")
def test_chat_streams_response(mock_stream):
    async def fake_stream(messages, model):
        yield "Hello"
        yield " World"

    mock_stream.return_value = fake_stream([], None)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hi there"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data: Hello" in body
    assert "data: [DONE]" in body
```

- [ ] **Step 9: Write integration tests for file upload**

```python
# backend/tests/test_files.py
import io
import csv
from fastapi.testclient import TestClient
from main import app
from auth.mock_provider import MockAuthProvider

client = TestClient(app)
_provider = MockAuthProvider(users="testuser", secret="local-dev-secret-change-me")


def _auth_header():
    token = _provider.login("testuser")
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_auth():
    response = client.post("/api/files/upload", files={"file": ("test.csv", b"data", "text/csv")})
    assert response.status_code == 401


def test_upload_rejects_disallowed_type():
    response = client.post(
        "/api/files/upload",
        files={"file": ("malware.exe", b"bad", "application/octet-stream")},
        headers=_auth_header(),
    )
    assert response.status_code == 400
    assert "file_type_not_allowed" in str(response.json())


def test_upload_blocks_ni_in_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "NI"])
    writer.writerow(["John", "AB123456C"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "uk_national_insurance"


def test_upload_clean_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Client", "Revenue"])
    writer.writerow(["Acme", "50000"])
    csv_bytes = output.getvalue().encode()

    response = client.post(
        "/api/files/upload",
        files={"file": ("data.csv", csv_bytes, "text/csv")},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == "data.csv"
    assert "Acme" in response.json()["file_content"]
```

- [ ] **Step 10: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (chat streaming test uses mock)

- [ ] **Step 11: Commit**

```bash
git add backend/main.py backend/routes/ backend/proxy/ backend/tests/test_chat.py backend/tests/test_files.py
git commit -m "feat: FastAPI app with auth, chat, file upload, and health routes"
```

---

## Task 5: Frontend — Types, API Service, Auth Hook

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/hooks/useAuth.ts`

- [ ] **Step 1: Create frontend/src/types.ts**

```typescript
// frontend/src/types.ts
export interface Message {
  role: "user" | "assistant";
  content: string;
  fileName?: string;
  fileContent?: string;
}

export interface FilterError {
  error: "content_filtered";
  message: string;
  rule: string;
}

export interface User {
  email: string;
  name: string;
}
```

- [ ] **Step 2: Create frontend/src/services/api.ts**

```typescript
// frontend/src/services/api.ts
import { Message, FilterError } from "../types";

const BASE = "/api";

function getHeaders(token: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchUsers(): Promise<string[]> {
  const res = await fetch(`${BASE}/auth/users`);
  const data = await res.json();
  return data.users;
}

export async function login(username: string): Promise<string> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  return data.token;
}

export async function uploadFile(
  file: File,
  token: string
): Promise<{ file_name: string; file_content: string } | FilterError> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/files/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (res.status === 403) {
    const detail = await res.json();
    return detail.detail as FilterError;
  }
  if (res.status === 400) {
    const detail = await res.json();
    return detail.detail as FilterError;
  }
  if (!res.ok) throw new Error("Upload failed");
  return await res.json();
}

export async function streamChat(
  messages: Message[],
  token: string,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: FilterError) => void
): Promise<void> {
  const body = {
    messages: messages.map((m) => ({
      role: m.role,
      content: m.content,
      file_content: m.fileContent || null,
      file_name: m.fileName || null,
    })),
  };

  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify(body),
  });

  if (res.status === 403) {
    const detail = await res.json();
    onError(detail.detail as FilterError);
    return;
  }

  if (!res.ok) throw new Error("Chat request failed");

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value);
    const lines = text.split("\n");
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") {
          onDone();
          return;
        }
        onChunk(data);
      }
    }
  }
  onDone();
}
```

- [ ] **Step 3: Create frontend/src/hooks/useAuth.ts**

```typescript
// frontend/src/hooks/useAuth.ts
import { useState, useCallback } from "react";
import { login as apiLogin } from "../services/api";

interface AuthState {
  token: string | null;
  username: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = sessionStorage.getItem("sh_token");
    const username = sessionStorage.getItem("sh_username");
    return { token, username };
  });

  const login = useCallback(async (username: string) => {
    const token = await apiLogin(username);
    sessionStorage.setItem("sh_token", token);
    sessionStorage.setItem("sh_username", username);
    setAuth({ token, username });
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem("sh_token");
    sessionStorage.removeItem("sh_username");
    setAuth({ token: null, username: null });
  }, []);

  return {
    token: auth.token,
    username: auth.username,
    isAuthenticated: auth.token !== null,
    login,
    logout,
  };
}
```

- [ ] **Step 4: Create frontend/src/main.tsx**

```typescript
// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.tsx frontend/src/types.ts frontend/src/services/ frontend/src/hooks/useAuth.ts
git commit -m "feat: frontend types, API service, and auth hook"
```

---

## Task 6: Frontend — Chat Hook and SessionStorage

**Files:**
- Create: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Create frontend/src/hooks/useChat.ts**

```typescript
// frontend/src/hooks/useChat.ts
import { useState, useCallback, useRef } from "react";
import { Message, FilterError } from "../types";
import { streamChat, uploadFile } from "../services/api";

const STORAGE_KEY = "sh_messages";

function loadMessages(): Message[] {
  const stored = sessionStorage.getItem(STORAGE_KEY);
  if (!stored) return [];
  try {
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

function saveMessages(messages: Message[]) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
}

export function useChat(token: string | null) {
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  const [isStreaming, setIsStreaming] = useState(false);
  const [filterError, setFilterError] = useState<FilterError | null>(null);
  const abortRef = useRef(false);

  const clearChat = useCallback(() => {
    setMessages([]);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  const dismissFilter = useCallback(() => {
    setFilterError(null);
  }, []);

  const sendMessage = useCallback(
    async (content: string, file?: File) => {
      if (!token) return;

      let fileContent: string | undefined;
      let fileName: string | undefined;

      if (file) {
        const uploadResult = await uploadFile(file, token);
        if ("error" in uploadResult) {
          setFilterError(uploadResult);
          return;
        }
        fileContent = uploadResult.file_content;
        fileName = uploadResult.file_name;
      }

      const userMessage: Message = { role: "user", content, fileName, fileContent };
      const updated = [...messages, userMessage];
      setMessages(updated);
      saveMessages(updated);

      const assistantMessage: Message = { role: "assistant", content: "" };
      const withAssistant = [...updated, assistantMessage];
      setMessages(withAssistant);
      setIsStreaming(true);
      abortRef.current = false;

      let accumulated = "";

      await streamChat(
        updated,
        token,
        (chunk) => {
          if (abortRef.current) return;
          accumulated += chunk;
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { role: "assistant", content: accumulated };
            return copy;
          });
        },
        () => {
          setIsStreaming(false);
          setMessages((prev) => {
            saveMessages(prev);
            return prev;
          });
        },
        (err) => {
          setIsStreaming(false);
          setFilterError(err);
          setMessages(updated);
          saveMessages(updated);
        }
      );
    },
    [token, messages]
  );

  return {
    messages,
    isStreaming,
    filterError,
    sendMessage,
    clearChat,
    dismissFilter,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: useChat hook with streaming and sessionStorage persistence"
```

---

## Task 7: Frontend — UI Components

**Files:**
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/components/LoginPage.tsx`
- Create: `frontend/src/components/MessageBubble.tsx`
- Create: `frontend/src/components/InputBar.tsx`
- Create: `frontend/src/components/FilterToast.tsx`
- Create: `frontend/src/components/ChatWindow.tsx`
- Create: `frontend/src/App.tsx`

- [ ] **Step 1: Create Header component**

```typescript
// frontend/src/components/Header.tsx
interface HeaderProps {
  username: string | null;
  onNewChat: () => void;
  onLogout: () => void;
}

export default function Header({ username, onNewChat, onLogout }: HeaderProps) {
  return (
    <header style={styles.header}>
      <div style={styles.brand}>
        <span style={styles.brandName}>Smith</span>
        <span style={styles.plus}>+</span>
        <span style={styles.brandName}>Howard</span>
        <span style={styles.divider} />
        <span style={styles.label}>CHAT</span>
      </div>
      <div style={styles.right}>
        <span style={styles.model}>Claude Sonnet</span>
        <button onClick={onNewChat} style={styles.newChat}>+ New Chat</button>
        {username && (
          <button onClick={onLogout} style={styles.avatar} title={username}>
            {username.slice(0, 2).toUpperCase()}
          </button>
        )}
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 24px",
    background: "#1a1a1a",
    borderBottom: "2px solid #c8102e",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  brandName: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#ffffff",
    fontFamily: "Georgia, serif",
  },
  plus: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#c8102e",
    fontFamily: "Georgia, serif",
  },
  divider: {
    width: "1px",
    height: "24px",
    background: "#444",
    margin: "0 12px",
  },
  label: {
    fontSize: "14px",
    fontWeight: 500,
    color: "#aaa",
    letterSpacing: "0.5px",
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
  },
  model: {
    fontSize: "11px",
    color: "#999",
    background: "#2a2a2a",
    padding: "4px 12px",
    borderRadius: "12px",
  },
  newChat: {
    background: "none",
    border: "1px solid #444",
    color: "#ccc",
    borderRadius: "6px",
    padding: "5px 12px",
    fontSize: "12px",
    cursor: "pointer",
  },
  avatar: {
    width: "30px",
    height: "30px",
    borderRadius: "50%",
    background: "#2a4a7f",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    color: "white",
    fontWeight: 600,
    border: "none",
    cursor: "pointer",
  },
};
```

- [ ] **Step 2: Create LoginPage component**

```typescript
// frontend/src/components/LoginPage.tsx
import { useState, useEffect } from "react";
import { fetchUsers } from "../services/api";

interface LoginPageProps {
  onLogin: (username: string) => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [users, setUsers] = useState<string[]>([]);
  const [selected, setSelected] = useState("");

  useEffect(() => {
    fetchUsers().then(setUsers);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selected) onLogin(selected);
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <span style={styles.brandName}>Smith</span>
          <span style={styles.plus}>+</span>
          <span style={styles.brandName}>Howard</span>
        </div>
        <p style={styles.subtitle}>Chat — Development Login</p>
        <form onSubmit={handleSubmit} style={styles.form}>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            style={styles.select}
          >
            <option value="">Select a user...</option>
            {users.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
          <button type="submit" disabled={!selected} style={styles.button}>
            Sign In
          </button>
        </form>
        <p style={styles.note}>
          This is a development login. In production, this will redirect to your corporate SSO.
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    background: "#f5f5f5",
  },
  card: {
    background: "#fff",
    borderRadius: "12px",
    padding: "48px",
    boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
    textAlign: "center",
    maxWidth: "400px",
    width: "100%",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "4px",
    marginBottom: "8px",
  },
  brandName: {
    fontSize: "28px",
    fontWeight: 700,
    color: "#1a1a1a",
    fontFamily: "Georgia, serif",
  },
  plus: {
    fontSize: "28px",
    fontWeight: 700,
    color: "#c8102e",
    fontFamily: "Georgia, serif",
  },
  subtitle: {
    color: "#666",
    fontSize: "14px",
    marginBottom: "32px",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  select: {
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #ddd",
    fontSize: "14px",
  },
  button: {
    padding: "12px",
    borderRadius: "8px",
    border: "none",
    background: "#1a1a1a",
    color: "#fff",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  note: {
    marginTop: "24px",
    fontSize: "11px",
    color: "#999",
  },
};
```

- [ ] **Step 3: Create MessageBubble component**

```typescript
// frontend/src/components/MessageBubble.tsx
import ReactMarkdown from "react-markdown";
import { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", gap: "10px" }}>
      {!isUser && (
        <div style={styles.badge}>S+H</div>
      )}
      <div style={isUser ? styles.userBubble : styles.assistantBubble}>
        {isUser ? (
          <>
            <p style={{ margin: 0 }}>{message.content}</p>
            {message.fileName && (
              <div style={styles.fileAttachment}>
                <span>📄</span> {message.fileName}
              </div>
            )}
          </>
        ) : (
          <div style={styles.markdown}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
            {isStreaming && <span style={styles.cursor} />}
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  badge: {
    minWidth: "28px",
    height: "28px",
    borderRadius: "6px",
    background: "#1a1a1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "10px",
    color: "#c8102e",
    fontWeight: 700,
    marginTop: "2px",
  },
  userBubble: {
    background: "#1a1a1a",
    borderRadius: "16px 16px 4px 16px",
    padding: "14px 18px",
    maxWidth: "65%",
    fontSize: "14px",
    color: "#f0f0f0",
    lineHeight: 1.5,
  },
  assistantBubble: {
    background: "#ffffff",
    border: "1px solid #e0e0e0",
    borderRadius: "16px 16px 16px 4px",
    padding: "14px 18px",
    maxWidth: "70%",
    fontSize: "14px",
    color: "#333",
    lineHeight: 1.7,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  fileAttachment: {
    marginTop: "10px",
    padding: "8px 12px",
    background: "#2a2a2a",
    borderRadius: "8px",
    fontSize: "12px",
    color: "#aaa",
  },
  markdown: {
    overflow: "hidden",
  },
  cursor: {
    display: "inline-block",
    width: "8px",
    height: "16px",
    background: "#c8102e",
    borderRadius: "2px",
    verticalAlign: "middle",
    animation: "blink 1s infinite",
  },
};
```

- [ ] **Step 4: Create InputBar component**

```typescript
// frontend/src/components/InputBar.tsx
import { useState, useRef } from "react";

interface InputBarProps {
  onSend: (content: string, file?: File) => void;
  disabled: boolean;
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() && !file) return;
    onSend(text.trim(), file || undefined);
    setText("");
    setFile(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div style={styles.container}>
      {file && (
        <div style={styles.filePreview}>
          📄 {file.name}
          <button onClick={() => setFile(null)} style={styles.removeFile}>✕</button>
        </div>
      )}
      <form onSubmit={handleSubmit} style={styles.form}>
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          style={styles.attach}
          title="Attach file"
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          hidden
          accept=".csv,.xlsx,.pdf,.txt,.png,.jpg"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Smith+Howard Chat..."
          style={styles.input}
          rows={1}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || (!text.trim() && !file)} style={styles.send}>
          Send
        </button>
      </form>
      <p style={styles.notice}>
        Messages are scanned for sensitive data before being sent. Conversations are not stored on the server.
      </p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "16px 80px 22px",
    background: "#f5f5f5",
    borderTop: "1px solid #e8e8e8",
  },
  filePreview: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    background: "#e8e8e8",
    padding: "4px 10px",
    borderRadius: "6px",
    fontSize: "12px",
    marginBottom: "8px",
  },
  removeFile: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "12px",
    color: "#666",
  },
  form: {
    display: "flex",
    alignItems: "flex-end",
    gap: "8px",
    background: "#ffffff",
    border: "1px solid #d0d0d0",
    borderRadius: "16px",
    padding: "12px 16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
  },
  attach: {
    background: "none",
    border: "none",
    fontSize: "18px",
    cursor: "pointer",
    padding: "2px",
  },
  input: {
    flex: 1,
    border: "none",
    outline: "none",
    fontSize: "14px",
    resize: "none",
    fontFamily: "inherit",
    lineHeight: 1.4,
  },
  send: {
    background: "#1a1a1a",
    border: "none",
    color: "white",
    borderRadius: "8px",
    padding: "7px 16px",
    fontSize: "13px",
    cursor: "pointer",
    fontWeight: 500,
  },
  notice: {
    textAlign: "center",
    marginTop: "8px",
    fontSize: "11px",
    color: "#aaa",
  },
};
```

- [ ] **Step 5: Create FilterToast component**

```typescript
// frontend/src/components/FilterToast.tsx
import { FilterError } from "../types";

interface FilterToastProps {
  error: FilterError;
  onDismiss: () => void;
}

export default function FilterToast({ error, onDismiss }: FilterToastProps) {
  return (
    <div style={styles.toast}>
      <span style={styles.icon}>⚠️</span>
      <span style={styles.message}>{error.message}</span>
      <button onClick={onDismiss} style={styles.dismiss}>✕</button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toast: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    background: "#fff3cd",
    border: "1px solid #ffc107",
    borderRadius: "8px",
    padding: "10px 16px",
    margin: "0 80px 12px",
    fontSize: "13px",
    color: "#856404",
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
  },
  icon: {
    fontSize: "16px",
  },
  message: {
    flex: 1,
  },
  dismiss: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "14px",
    color: "#856404",
  },
};
```

- [ ] **Step 6: Create ChatWindow component**

```typescript
// frontend/src/components/ChatWindow.tsx
import { useEffect, useRef } from "react";
import { Message } from "../types";
import MessageBubble from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  isStreaming: boolean;
}

export default function ChatWindow({ messages, isStreaming }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div style={styles.empty}>
        <div style={styles.welcomeTitle}>
          Smith<span style={{ color: "#c8102e" }}>+</span>Howard Chat
        </div>
        <p style={styles.welcomeSub}>Your secure AI assistant for tax, accounting & advisory work</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {messages.map((msg, i) => (
        <MessageBubble
          key={i}
          message={msg}
          isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: "auto",
    padding: "28px 80px",
    display: "flex",
    flexDirection: "column",
    gap: "24px",
    background: "#f5f5f5",
  },
  empty: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    background: "#f5f5f5",
  },
  welcomeTitle: {
    fontSize: "28px",
    fontWeight: 700,
    color: "#1a1a1a",
    fontFamily: "Georgia, serif",
  },
  welcomeSub: {
    fontSize: "13px",
    color: "#777",
    marginTop: "4px",
  },
};
```

- [ ] **Step 7: Create App component**

```typescript
// frontend/src/App.tsx
import { useAuth } from "./hooks/useAuth";
import { useChat } from "./hooks/useChat";
import Header from "./components/Header";
import LoginPage from "./components/LoginPage";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import FilterToast from "./components/FilterToast";

export default function App() {
  const { token, username, isAuthenticated, login, logout } = useAuth();
  const { messages, isStreaming, filterError, sendMessage, clearChat, dismissFilter } = useChat(token);

  if (!isAuthenticated) {
    return <LoginPage onLogin={login} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <Header username={username} onNewChat={clearChat} onLogout={logout} />
      <ChatWindow messages={messages} isStreaming={isStreaming} />
      {filterError && <FilterToast error={filterError} onDismiss={dismissFilter} />}
      <InputBar onSend={sendMessage} disabled={isStreaming} />
      <style>{`@keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0; } }`}</style>
    </div>
  );
}
```

- [ ] **Step 8: Verify frontend builds**

Run: `cd frontend && npm install && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 9: Commit**

```bash
git add frontend/src/
git commit -m "feat: React chat UI with S+H branding, streaming, and file upload"
```

---

## Task 8: Docker Compose + Nginx

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `nginx/nginx.conf`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create frontend Dockerfile**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

- [ ] **Step 3: Create nginx.conf**

```nginx
# nginx/nginx.conf
server {
    listen 80;
    server_name localhost;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    client_max_body_size 20M;
}
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    env_file: .env
    volumes:
      - ./config:/app/config:ro
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
    depends_on:
      - backend
```

- [ ] **Step 5: Verify Docker Compose config is valid**

Run: `docker compose config --quiet`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile nginx/ docker-compose.yml
git commit -m "feat: Docker Compose setup with Nginx reverse proxy"
```

---

## Task 9: Documentation — README and Production Guide

**Files:**
- Modify: `README.md`
- Create: `docs/production-guide.md`

- [ ] **Step 1: Write README.md**

```markdown
# Smith+Howard Chat

Enterprise AI chat gateway powered by Claude. Provides a familiar ChatGPT-like experience with content filtering for sensitive financial data.

## Quick Start (PoC / Local Development)

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### Setup

1. Clone the repository:
   ```bash
   git clone https://code.roche.com/ai-uk/chatgateway.git
   cd chatgateway
   ```

2. Create your environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

4. Start the application:
   ```bash
   docker compose up --build
   ```

5. Open http://localhost in your browser

6. Select a mock user from the dropdown and start chatting

### Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # edit with your API key
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to `localhost:8000` automatically.

### Running Tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Architecture

```
Browser → Nginx (port 80) → FastAPI (port 8000) → Claude API
                ↓
         React SPA (static)
```

- **No database** — conversations exist only in the browser session
- **Content filtering** — messages and files are scanned for sensitive data (NI numbers, card numbers, bank details) before reaching Claude
- **Mock SSO** — simple user picker for development; production-ready OIDC interface underneath

## Content Filter

Rules are configured in `config/content-filter.yaml`. Edit this file to add or modify detection patterns. No code changes or restarts required (rules are loaded at startup — restart the backend container to pick up changes).

Currently detects:
- UK National Insurance numbers
- Credit/debit card numbers (Luhn validation)
- UK bank account numbers (sort code + account)
- Email addresses (warns, does not block)

## Security Model

- Conversations are **never stored server-side** — they exist only in the browser's sessionStorage
- Files are scanned in memory and relayed to Claude — **never written to disk**
- All requests require a valid JWT token
- Content filter runs **server-side** — cannot be bypassed by client manipulation

## Going to Production

See [docs/production-guide.md](docs/production-guide.md) for the complete checklist to move from PoC to production deployment.

### Summary of changes needed:

| Area | What to do |
|------|-----------|
| Auth | Set `AUTH_PROVIDER=oidc`, register Azure AD app, configure OIDC env vars |
| TLS | Configure Nginx with real certificate |
| API Key | Set production Anthropic API key |
| Content filter | Review and expand rules for your specific data |
| Domain | Update Nginx `server_name` and OIDC redirect URI |
| Secrets | Move from `.env` file to Vault or K8s secrets |
| Logo | Replace text mark with actual S+H logo asset |

## Project Structure

```
chatgateway/
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment template
├── config/
│   └── content-filter.yaml     # Content filter rules
├── backend/                    # FastAPI gateway
│   ├── auth/                   # Authentication (mock + OIDC-ready)
│   ├── filter/                 # Content filtering engine
│   ├── proxy/                  # Claude API streaming proxy
│   └── routes/                 # API endpoints
├── frontend/                   # React SPA
│   └── src/
│       ├── components/         # UI components
│       ├── hooks/              # State management
│       └── services/           # API client
└── nginx/                      # Reverse proxy config
```
```

- [ ] **Step 2: Write production guide**

```markdown
# Production Deployment Guide

This guide covers every step to move Smith+Howard Chat from the local PoC to a production deployment.

## Prerequisites

- A domain name (e.g., `chat.smithhoward.com`)
- Access to your corporate identity provider (Azure AD / Entra ID)
- A production Anthropic API key
- A TLS certificate for the domain
- A host to run Docker Compose (or equivalent container platform)

## Step 1: Register OIDC Application

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Create a new registration:
   - Name: "Smith+Howard Chat"
   - Redirect URI: `https://chat.smithhoward.com/api/auth/callback`
   - Supported account types: "Accounts in this organizational directory only"
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Under Certificates & secrets, create a new client secret
5. Under Token configuration, add optional claims: `email`, `name`

## Step 2: Configure Environment

Update your `.env` (or secrets manager):

```env
# Switch from mock to OIDC
AUTH_PROVIDER=oidc
OIDC_ISSUER=https://login.microsoftonline.com/{tenant-id}/v2.0
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://chat.smithhoward.com/api/auth/callback

# Production Claude key
ANTHROPIC_API_KEY=sk-ant-production-key

# Remove mock-specific vars
# MOCK_USERS (no longer needed)
# JWT_SECRET (tokens come from Azure AD now)
```

## Step 3: Configure TLS

Update `nginx/nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name chat.smithhoward.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # ... rest of config unchanged ...
}

server {
    listen 80;
    server_name chat.smithhoward.com;
    return 301 https://$host$request_uri;
}
```

Mount certificates in `docker-compose.yml`:

```yaml
frontend:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - /path/to/certs:/etc/nginx/ssl:ro
```

## Step 4: Review Content Filter Rules

Edit `config/content-filter.yaml` to add patterns specific to your data:

- Add any internal reference number formats
- Add patterns for client-specific sensitive data
- Review the email rule — decide whether to block or warn
- Consider adding phone number patterns

## Step 5: Configure DNS

Create an A record (or CNAME) pointing `chat.smithhoward.com` to your host's IP address.

## Step 6: Update CORS

In `backend/main.py`, update the CORS origin:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.smithhoward.com"],
    ...
)
```

## Step 7: Add Logo

Replace the text-based logo with the actual Smith+Howard horizontal logo:

1. Place `logo.svg` (or `logo.png`) in `frontend/public/`
2. Update `frontend/src/components/Header.tsx` to use the image:
   ```tsx
   <img src="/logo.svg" alt="Smith+Howard" style={{ height: "28px" }} />
   ```

## Step 8: Deploy

```bash
docker compose up --build -d
```

Verify:
- Visit `https://chat.smithhoward.com`
- Confirm redirect to Azure AD login
- Log in with a corporate account
- Send a test message
- Verify content filter blocks a test NI number

## Step 9: Operational Considerations

### Logging

Add structured logging to the backend. Recommended: add a logging middleware that records request metadata (user, endpoint, status code, response time) without logging message content.

### Rate Limiting (Optional)

To prevent runaway API costs, add a Redis container and rate limiting:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

Then add a rate limit middleware in FastAPI using `slowapi` or similar.

### Monitoring (Optional)

Add a `/api/metrics` endpoint exposing:
- Total requests
- Requests per user
- Content filter blocks
- Claude API latency

### Backup

Since there's no server-side data storage, backup needs are minimal:
- Back up the `.env` file (or confirm secrets are in your vault)
- Back up `config/content-filter.yaml` (checked into git)
- Back up any TLS certificates

## Security Checklist

Before go-live, verify:

- [ ] OIDC flow works end-to-end with Azure AD
- [ ] TLS configured with valid certificate (check with `curl -v`)
- [ ] `.env` not committed to git
- [ ] Content filter blocks test cases for all patterns
- [ ] File upload rejects disallowed types
- [ ] CORS restricted to production domain only
- [ ] No development/mock endpoints accessible (`/api/auth/users` should be disabled in prod)
- [ ] Docker containers run as non-root user
- [ ] Nginx `client_max_body_size` set appropriately
- [ ] Rate limiting in place (if using)
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/production-guide.md
git commit -m "docs: README with quick start and production deployment guide"
```

---

## Task 10: Final Integration Test

**Files:** None new — verify everything works together.

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Verify frontend builds cleanly**

Run: `cd frontend && npm run build`
Expected: No TypeScript errors, `dist/` produced

- [ ] **Step 3: Test Docker Compose builds**

Run: `docker compose build`
Expected: All images build successfully

- [ ] **Step 4: Start the stack and verify health endpoint**

Run: `docker compose up -d && sleep 5 && curl http://localhost/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 5: Verify auth flow works**

Run: `curl http://localhost/api/auth/users`
Expected: `{"users":["john.doe","jane.smith","admin"]}`

Run: `curl -X POST http://localhost/api/auth/login -H "Content-Type: application/json" -d '{"username":"john.doe"}'`
Expected: `{"token":"eyJ..."}`

- [ ] **Step 6: Verify content filter blocks sensitive data**

Run (using the token from step 5):
```bash
TOKEN="<token from step 5>"
curl -X POST http://localhost/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"My NI is AB123456C"}]}'
```
Expected: 403 response with `"rule": "uk_national_insurance"`

- [ ] **Step 7: Stop the stack**

Run: `docker compose down`

- [ ] **Step 8: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix: integration test fixes"
```

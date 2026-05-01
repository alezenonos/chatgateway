# Smith+Howard Chat

Enterprise AI chat gateway that gives accounting, tax, and advisory teams a familiar ChatGPT-like experience with built-in content filtering for sensitive financial data.

> **Status:** Proof of Concept — designed for easy upgrade to production. See [Going to Production](#going-to-production).

## Screenshots

### Login Page
> *Mock SSO login — select a user from the dropdown. In production, this redirects to Azure AD.*

![Login Page](docs/screenshots/login.png)

### Chat Interface
> *Streaming responses with Smith+Howard branding. Model badge shows the active LLM.*

![Chat Interface](docs/screenshots/chat.png)

### Content Filter
> *Messages containing sensitive data (NI numbers, card numbers, etc.) are blocked with a clear explanation.*

![Content Filter](docs/screenshots/filter-blocked.png)

---

## How It Works

```mermaid
graph LR
    User[/"User (Browser)"/]
    Nginx["Nginx<br/>Reverse Proxy"]
    FastAPI["FastAPI Gateway<br/>• Auth validation<br/>• Content filtering<br/>• Stream proxy"]
    LLM["LLM API<br/>(OpenRouter / Anthropic)"]
    IdP["Identity Provider<br/>Mock (PoC) / Azure AD (Prod)"]

    User -->|HTTPS| Nginx
    Nginx -->|/api/*| FastAPI
    Nginx -->|static files| User
    FastAPI -->|streaming| LLM
    FastAPI -.->|validate JWT| IdP

    style User fill:#f5f5f5,stroke:#333,color:#333
    style Nginx fill:#2a4a7f,stroke:#1a1a1a,color:#fff
    style FastAPI fill:#1a1a1a,stroke:#c8102e,color:#fff
    style LLM fill:#6366f1,stroke:#333,color:#fff
    style IdP fill:#444,stroke:#333,color:#fff
```

**Three containers, no database.** The FastAPI gateway sits between the user and the LLM — it validates authentication, scans messages for sensitive data, and streams responses back. Conversations live only in the browser's `sessionStorage` and are never stored server-side.

### LLM Providers

The gateway supports multiple LLM backends, switched via environment variable:

| Provider | Config | Default Model |
|----------|--------|---------------|
| **OpenRouter** (default) | `LLM_PROVIDER=openrouter` | `liquid/lfm-2.5-1.2b-instruct:free` |
| **Anthropic** | `LLM_PROVIDER=anthropic` | `claude-sonnet-4-20250514` |

OpenRouter gives access to many models (including free ones) through a single API key. See [openrouter.ai/models](https://openrouter.ai/models) for available models.

---

## Request Flow

Every message goes through this pipeline before reaching the LLM:

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant N as Nginx
    participant G as FastAPI Gateway
    participant F as Content Filter
    participant L as LLM API

    U->>N: POST /api/chat + Bearer JWT
    N->>G: Proxy request
    G->>G: Validate JWT (signature, expiry, claims)
    G->>F: Scan message text
    
    alt Sensitive data detected
        F-->>G: BLOCK (rule: uk_national_insurance)
        G-->>U: 403 + reason
    else Clean message
        F-->>G: PASS
        G->>L: Stream request (messages + model)
        loop Token by token
            L-->>G: text chunk
            G-->>U: SSE: data: chunk
        end
        G-->>U: SSE: data: [DONE]
    end
```

### File Upload Flow

Files follow an extra scanning step:

```mermaid
sequenceDiagram
    participant U as User
    participant G as Gateway
    participant S as File Scanner
    participant F as Content Filter

    U->>G: POST /api/files/upload (multipart)
    G->>G: Check file extension against allowlist
    
    alt Disallowed file type
        G-->>U: 400 "file type not allowed"
    else Allowed type
        G->>S: Extract text content (CSV cells, Excel values, plain text)
        S-->>G: Extracted text
        G->>F: Scan extracted text
        alt Sensitive data in file
            F-->>G: BLOCK
            G-->>U: 403 + rule that triggered
        else Clean file
            F-->>G: PASS
            G-->>U: 200 + file reference (held in memory, never written to disk)
        end
    end
```

---

## Authentication

The auth system has one interface with two backends, swapped by environment variable:

```mermaid
graph TD
    subgraph "PoC Mode (AUTH_PROVIDER=mock)"
        LP["Login Page<br/>User picker dropdown"]
        MP["Mock Provider<br/>Issues JWTs locally"]
        LP --> MP
    end

    subgraph "Production Mode (AUTH_PROVIDER=oidc)"
        RD["Redirect to Azure AD"]
        CB["OIDC Callback<br/>Exchange code for JWT"]
        RD --> CB
    end

    MP --> JWT["JWT Token<br/>Same claims structure<br/>(sub, email, name, roles)"]
    CB --> JWT
    JWT --> GW["FastAPI Gateway<br/>Validates token identically<br/>regardless of issuer"]

    style LP fill:#fff3cd,stroke:#ffc107,color:#333
    style MP fill:#fff3cd,stroke:#ffc107,color:#333
    style RD fill:#d4edda,stroke:#28a745,color:#333
    style CB fill:#d4edda,stroke:#28a745,color:#333
    style JWT fill:#e8e8e8,stroke:#333,color:#333
    style GW fill:#1a1a1a,stroke:#c8102e,color:#fff
```

**No code changes to switch** — only environment configuration. The JWT claims are identical in both modes, so the gateway validates them the same way.

---

## Content Filter & Data Handling

Server-side filtering scans every message and file before it reaches the LLM. Rules are configured in `config/content-filter.yaml` — no code changes needed.

| What it detects | How | Action |
|---|---|---|
| UK National Insurance numbers | Regex pattern matching | **Block** + tell user why |
| Credit/debit card numbers | Luhn algorithm validation | **Block** + tell user why |
| UK bank account numbers | Sort code + account pattern | **Block** + tell user why |
| Email addresses | Standard email regex | **Warn** (allow with notice) |
| Disallowed file types | Extension allowlist | **Block** upload |

**File scanning** goes deeper than filenames — CSV cells and Excel cell values are extracted and scanned individually.

For a comprehensive overview of how financial data is handled, current guardrails, known gaps, and production recommendations, see **[docs/data-handling.md](docs/data-handling.md)**.

### Adding a new rule

Edit `config/content-filter.yaml`:

```yaml
rules:
  # ... existing rules ...
  
  - name: phone_number
    pattern: '(\+44|0)\d{10,11}'
    action: block
    message: "Message blocked: contains what appears to be a UK phone number"
```

Restart the backend container to pick up changes.

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An **OpenRouter API key** ([openrouter.ai/keys](https://openrouter.ai/keys)) — free tier available

### Setup

```bash
git clone https://code.roche.com/ai-uk/chatgateway.git
cd chatgateway
cp .env.example .env
# Edit .env — add your OPENROUTER_API_KEY
docker compose up --build
```

Open **http://localhost**, select a mock user, start chatting.

### Development (without Docker)

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
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

Vite proxies `/api/*` to `localhost:8000` automatically.

### Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

56 tests covering: auth (unit + integration), content filter (regex, Luhn, file scanners), API routes (chat, files, health), proxy (provider selection), and regression edge cases. 86% code coverage.

---

## API Reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/health` | GET | No | Health check — returns `{"status": "ok"}` |
| `/api/config` | GET | No | Returns active model name and LLM provider |
| `/api/auth/users` | GET | No | List available mock users (PoC only) |
| `/api/auth/login` | POST | No | Mock login — returns JWT. Body: `{"username": "john.doe"}` |
| `/api/chat` | POST | Yes | Send message to LLM (streaming SSE response). Body: `{"messages": [...]}` |
| `/api/files/upload` | POST | Yes | Upload file for scanning. Multipart form with `file` field |

### Chat request example

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john.doe"}' | jq -r '.token')

# Send a message (streaming)
curl -N http://localhost/api/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Summarise UK tax obligations for Q3"}]}'
```

### Content filter error response

```json
{
  "detail": {
    "error": "content_filtered",
    "message": "Message blocked: contains what appears to be a National Insurance number",
    "rule": "uk_national_insurance"
  }
}
```

---

## Security Model

```mermaid
graph TB
    subgraph "What IS stored"
        BS["Browser sessionStorage<br/>(conversation history)"]
        CF["config/content-filter.yaml<br/>(filter rules, in git)"]
        ENV[".env file<br/>(API key, JWT secret)"]
    end

    subgraph "What is NOT stored"
        NC["Conversations<br/>Never on server"]
        NF["Uploaded files<br/>Never written to disk"]
        NL["Message content logs<br/>Not logged"]
    end

    style BS fill:#fff3cd,stroke:#ffc107,color:#333
    style CF fill:#d4edda,stroke:#28a745,color:#333
    style ENV fill:#f8d7da,stroke:#dc3545,color:#333
    style NC fill:#f5f5f5,stroke:#999,color:#666
    style NF fill:#f5f5f5,stroke:#999,color:#666
    style NL fill:#f5f5f5,stroke:#999,color:#666
```

- **No server-side conversation storage** — sessionStorage only (cleared when tab closes)
- **Files scanned in memory, relayed to LLM, never written to disk**
- **JWT authentication** on every API request
- **Content filter is server-side** — cannot be bypassed from the browser
- **CORS restricted** to the frontend origin

For full details on data handling, known gaps, and production recommendations, see **[docs/data-handling.md](docs/data-handling.md)**.

---

## Going to Production

See [docs/production-guide.md](docs/production-guide.md) for step-by-step instructions.

```mermaid
graph LR
    subgraph "PoC (now)"
        M1["Mock login<br/>(user picker)"]
        M2["HTTP<br/>(localhost)"]
        M3[".env file<br/>(secrets)"]
        M4["Default filter<br/>rules"]
        M5["Text logo"]
    end

    subgraph "Production"
        P1["Azure AD SSO<br/>(OIDC)"]
        P2["HTTPS + TLS<br/>(real cert)"]
        P3["Vault / K8s<br/>secrets"]
        P4["Reviewed +<br/>expanded rules"]
        P5["S+H logo<br/>asset"]
    end

    M1 -->|"AUTH_PROVIDER=oidc"| P1
    M2 -->|"nginx ssl config"| P2
    M3 -->|"swap env source"| P3
    M4 -->|"edit YAML"| P4
    M5 -->|"replace logo.svg"| P5

    style M1 fill:#fff3cd,stroke:#ffc107,color:#333
    style M2 fill:#fff3cd,stroke:#ffc107,color:#333
    style M3 fill:#fff3cd,stroke:#ffc107,color:#333
    style M4 fill:#fff3cd,stroke:#ffc107,color:#333
    style M5 fill:#fff3cd,stroke:#ffc107,color:#333
    style P1 fill:#d4edda,stroke:#28a745,color:#333
    style P2 fill:#d4edda,stroke:#28a745,color:#333
    style P3 fill:#d4edda,stroke:#28a745,color:#333
    style P4 fill:#d4edda,stroke:#28a745,color:#333
    style P5 fill:#d4edda,stroke:#28a745,color:#333
```

### Quick reference

| Area | PoC | Production | How to switch |
|------|-----|-----------|---------------|
| **Auth** | Mock user picker | Azure AD / Entra OIDC | `AUTH_PROVIDER=oidc` + OIDC env vars |
| **TLS** | HTTP on localhost | HTTPS with real cert | Nginx ssl config + cert mount |
| **LLM** | OpenRouter (free model) | Anthropic or OpenRouter (paid) | `LLM_PROVIDER` + API key env vars |
| **Content filter** | Default rules | Reviewed/expanded | Edit `config/content-filter.yaml` |
| **Domain** | localhost | chat.smithhoward.com | Nginx `server_name` + DNS |
| **Secrets** | `.env` file | Vault / K8s secrets | Swap env var source |
| **Logo** | Text mark | S+H logo asset | Replace in `frontend/public/` |

---

## Project Structure

```
chatgateway/
├── .gitlab-ci.yml              # CI pipeline (tests, lint, build)
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment variable template
│
├── config/
│   └── content-filter.yaml     # Content filter rules (YAML)
│
├── backend/                    # Python / FastAPI
│   ├── main.py                 # App entry point
│   ├── config.py               # Settings (pydantic-settings)
│   ├── auth/
│   │   ├── provider.py         # Auth provider protocol
│   │   ├── mock_provider.py    # Mock IdP (PoC)
│   │   └── middleware.py       # JWT validation
│   ├── filter/
│   │   ├── engine.py           # Content filter (scan text)
│   │   ├── rules.py            # YAML rule loader
│   │   ├── luhn.py             # Luhn algorithm (card detection)
│   │   └── scanners.py         # CSV/Excel text extraction
│   ├── proxy/
│   │   └── claude.py           # LLM streaming proxy (OpenRouter + Anthropic)
│   ├── routes/
│   │   ├── auth.py             # /api/auth/* endpoints
│   │   ├── chat.py             # /api/chat endpoint
│   │   ├── files.py            # /api/files/upload endpoint
│   │   └── health.py           # /api/health + /api/config endpoints
│   └── tests/                  # 56 tests (pytest, 86% coverage)
│
├── frontend/                   # React 18 / TypeScript / Vite
│   └── src/
│       ├── App.tsx             # Root component (login vs chat)
│       ├── components/
│       │   ├── Header.tsx      # S+H branded header + model badge
│       │   ├── LoginPage.tsx   # Mock login page
│       │   ├── ChatWindow.tsx  # Message list + auto-scroll
│       │   ├── MessageBubble.tsx # Markdown rendering
│       │   ├── InputBar.tsx    # Text input + file attach
│       │   └── FilterToast.tsx # Content filter warning
│       ├── hooks/
│       │   ├── useAuth.ts      # Token management
│       │   └── useChat.ts      # Streaming + sessionStorage
│       └── services/
│           └── api.ts          # API client (fetch + SSE)
│
├── nginx/
│   └── nginx.conf              # Reverse proxy configuration
│
└── docs/
    ├── production-guide.md     # PoC-to-production checklist
    └── data-handling.md        # Financial data handling & security guardrails
```

---

## CI/CD

GitLab CI runs on every push and merge request:

| Stage | Job | What it does |
|---|---|---|
| **test** | `backend-unit-tests` | 56 pytest tests + 86% coverage report |
| **test** | `frontend-typecheck` | TypeScript type checking (`tsc --noEmit`) |
| **test** | `dockerfile-lint` | Hadolint Dockerfile best-practice linting |
| **build** | `frontend-build` | Vite production build |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite |
| LLM (default) | OpenRouter API (Liquid LFM 2.5, free) |
| LLM (alternative) | Anthropic Claude API (streaming) |
| Auth (PoC) | PyJWT, mock IdP |
| Auth (prod) | Azure AD OIDC |
| Content filter | Regex, Luhn algorithm, PyYAML, openpyxl |
| Markdown | react-markdown |
| Reverse proxy | Nginx |
| Containers | Docker, Docker Compose |
| CI | GitLab CI + Hadolint |

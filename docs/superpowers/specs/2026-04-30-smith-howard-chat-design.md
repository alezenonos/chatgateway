# Smith+Howard Chat — Design Spec

Enterprise AI chat gateway that gives Smith+Howard users a ChatGPT-like experience powered by Claude, with content filtering for sensitive financial data. Built as a PoC with a clear production upgrade path.

## System Overview

- **Product:** Smith+Howard Chat
- **Users:** 50–500 enterprise users (accounting, tax, advisory teams)
- **LLM Backend:** Anthropic Claude API (single API key, managed centrally)
- **Auth:** OIDC/SAML-ready, mock IdP for PoC
- **Data storage:** None server-side — conversations exist only in the browser session
- **Deployment:** Docker Compose, self-hosted
- **Tenancy:** Single-tenant

## Architecture

Three containers, no database.

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose Host                    │
│                                                         │
│  ┌────────────┐    ┌─────────────────┐    ┌───────────┐│
│  │            │    │                 │    │           ││
│  │  Nginx     │───▶│  FastAPI        │───▶│ Claude API││
│  │  (reverse  │    │  Gateway        │    │ (external)││
│  │   proxy +  │    │                 │    │           ││
│  │   static)  │    │  • Auth         │    └───────────┘│
│  │            │    │  • Content      │                  │
│  └─────┬──────┘    │    filter       │                  │
│        │           │  • Stream proxy │                  │
│        ▼           │  • File relay   │                  │
│  ┌────────────┐    │                 │                  │
│  │ React SPA  │    └─────────────────┘                  │
│  │ (static)   │                                         │
│  └────────────┘    Conversations in browser only        │
│                                                         │
└─────────────────────────────────────────────────────────┘
        │
        │ OIDC (mock in PoC)
        ▼
  ┌────────────┐
  │ IdP        │
  │ (mock /    │
  │  Azure AD) │
  └────────────┘
```

### Nginx

- Serves the React SPA as static files
- Reverse-proxies `/api/*` to FastAPI
- Handles TLS termination (self-signed for PoC, real cert for production)

### FastAPI Gateway

- Validates JWT tokens (from mock IdP or Azure AD — same code path)
- Runs content filter on outgoing messages and uploaded files
- Proxies streaming requests to Claude API via SSE
- Relays file uploads to Claude — files are never persisted on the server

### React SPA

- Chat interface branded as Smith+Howard Chat
- Stores conversation in browser `sessionStorage`
- Handles streaming responses, file attachments, markdown rendering
- Shows content filter warnings as toast notifications

## Request Flow

```
User sends message (+ optional file)
        │
        ▼
  React SPA → POST /api/chat (JSON + multipart file, Authorization: Bearer <jwt>)
        │
        ▼
  FastAPI Gateway:
    1. Validate JWT (signature, expiry, claims)
    2. Content filter — scan message text + file contents
       ├── PASS → proxy to Claude API (streaming)
       └── BLOCK → return 403 + reason ("contains National Insurance number")
        │
        ▼
  Claude API (streaming response)
        │
        ▼
  FastAPI streams SSE back to React SPA
        │
        ▼
  React renders response with markdown, code highlighting, streaming cursor
```

## Content Filtering

Server-side filtering on every request before it reaches Claude. Rules are configured in a YAML file — no code changes needed to update patterns.

### Initial Filter Rules

| Category | Pattern | Action |
|---|---|---|
| UK National Insurance | `[A-Z]{2}\d{6}[A-Z]` | Block + warn user |
| Credit/Debit Card | Luhn-valid 13–19 digit sequences | Block + warn user |
| Bank Account (UK) | Sort code + account number patterns | Block + warn user |
| Email addresses | Standard email regex | Warn (allow with confirmation) |
| File types | Allowlist: `.csv`, `.xlsx`, `.pdf`, `.txt`, `.png`, `.jpg` | Block disallowed types |

### Filter Design

- Runs server-side only — cannot be bypassed by client manipulation
- File content is scanned: CSV/Excel cell values are extracted and checked, not just filenames
- Filter response tells the user which rule triggered and why
- Rules loaded from `config/content-filter.yaml` at startup

### Example `content-filter.yaml`

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
    message: "Warning: your message contains an email address. Continue?"

allowed_file_types:
  - .csv
  - .xlsx
  - .pdf
  - .txt
  - .png
  - .jpg
```

## Authentication

One auth interface, two backends swapped by environment variable.

### Token Claims (identical in both modes)

```json
{
  "sub": "user-uuid",
  "email": "john.doe@smithhoward.com",
  "name": "John Doe",
  "roles": ["user"],
  "iat": 1714400000,
  "exp": 1714486400,
  "iss": "mock-idp"
}
```

### PoC Mode (`AUTH_PROVIDER=mock`)

- Mock IdP: simple login page with a user-picker dropdown (no password)
- Issues real JWTs with the same claims structure Azure AD would use
- Mock users configured via env var: `MOCK_USERS=john.doe,jane.smith,admin`
- JWT signed with a local secret (`JWT_SECRET` env var)

### Production Mode (`AUTH_PROVIDER=oidc`)

- Redirects to Azure AD/Entra ID for OIDC login
- Validates tokens against Azure AD's JWKS endpoint
- No code changes — only environment configuration

### Environment Configuration

```env
# PoC (local)
AUTH_PROVIDER=mock
MOCK_USERS=john.doe,jane.smith,admin
JWT_SECRET=local-dev-secret-key

# Production (future)
AUTH_PROVIDER=oidc
OIDC_ISSUER=https://login.microsoftonline.com/{tenant}/v2.0
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://chat.smithhoward.com/callback
```

## Chat UI

Branded Smith+Howard Chat interface with a clean, professional light theme.

### Layout

- **Header:** Dark bar with "Smith+Howard" in white serif, red "+" accent (#c8102e), "CHAT" label, model badge, user avatar, "New Chat" button
- **Chat area:** Light gray background (#f5f5f5), user messages in dark bubbles (right-aligned), assistant messages in white bubbles with S+H badge (left-aligned)
- **Input area:** White input bar with paperclip attachment button and send button
- **Footer:** Privacy notice — "Messages are scanned for sensitive data before being sent. Conversations are not stored on the server."

### Features

- **Streaming responses** — token-by-token with blinking cursor (red #c8102e)
- **File attachments** — shown inline in the message bubble with filename and size
- **Markdown rendering** — headings, bold, lists, code blocks with syntax highlighting
- **Content filter toast** — amber warning bar when a message is blocked, with the specific reason
- **New Chat** — clears `sessionStorage` and resets the conversation
- **No sidebar/history** — since nothing persists server-side, no conversation list needed
- **Model badge** — shows which Claude model is active (configurable server-side)

### Branding

- Primary color: black (#1a1a1a)
- Accent color: Smith+Howard red (#c8102e) — used sparingly on the "+", streaming cursor, and assistant avatar
- Typography: Georgia (serif) for the brand name, system sans-serif for body text
- Logo: text mark for PoC, swap for actual S+H horizontal logo asset when provided

## Project Structure

```
chatgateway/
├── docker-compose.yml
├── .env.example
├── config/
│   └── content-filter.yaml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # FastAPI app entry
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── provider.py          # Auth provider interface
│   │   ├── mock_provider.py     # Mock IdP for PoC
│   │   └── oidc_provider.py     # Azure AD OIDC for production
│   ├── filter/
│   │   ├── __init__.py
│   │   ├── engine.py            # Content filter engine
│   │   ├── rules.py             # Rule loading from YAML
│   │   └── scanners.py          # File content scanners (CSV, Excel)
│   └── proxy/
│       ├── __init__.py
│       └── claude.py            # Claude API streaming proxy
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx    # Main chat container
│   │   │   ├── MessageBubble.tsx # User/assistant message rendering
│   │   │   ├── InputBar.tsx      # Text input + file attach
│   │   │   ├── Header.tsx        # S+H branded header
│   │   │   ├── FilterToast.tsx   # Content filter warning
│   │   │   └── LoginPage.tsx     # Mock login / SSO redirect
│   │   ├── hooks/
│   │   │   ├── useChat.ts        # Chat state + streaming logic
│   │   │   └── useAuth.ts        # Auth token management
│   │   └── services/
│   │       └── api.ts            # API client (fetch + SSE)
│   └── public/
│       └── index.html
└── nginx/
    ├── nginx.conf
    └── Dockerfile
```

## API Endpoints

### `POST /api/auth/login`

PoC: accepts a username from the mock user list, returns a JWT.
Production: initiates OIDC redirect.

### `GET /api/auth/callback`

OIDC callback — exchanges auth code for JWT. Not used in mock mode.

### `POST /api/chat`

Main chat endpoint. Accepts JSON body with messages array. If the user attached files, the frontend first uploads them via `/api/files/upload`, receives file references, and includes those references in the messages array. Streams response via SSE.

**Request (text only):**
```json
{
  "messages": [
    {"role": "user", "content": "Analyse this report..."}
  ],
  "model": "claude-sonnet-4-20250514"
}
```

**Request (with file):**
```json
{
  "messages": [
    {"role": "user", "content": "Analyse this report...", "files": [{"id": "temp-uuid", "name": "q3-revenue.xlsx", "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}]}
  ],
  "model": "claude-sonnet-4-20250514"
}
```

**Response:** Server-Sent Events stream of Claude's response chunks.

**Error (content filter):**
```json
{
  "error": "content_filtered",
  "message": "Message blocked: contains what appears to be a National Insurance number",
  "rule": "uk_national_insurance"
}
```

### `POST /api/files/upload`

File upload endpoint. Accepts multipart file, runs content filter scan on file contents, and returns a temporary file reference (held in memory for the duration of the request — not persisted to disk). The reference is used in the subsequent `/api/chat` call to include the file in Claude's context.

### `GET /api/health`

Health check for Docker Compose and monitoring.

## PoC-to-Production Path

Documented in the project README and a dedicated `docs/production-guide.md`.

### What changes for production

| Area | PoC (local) | Production | How to switch |
|---|---|---|---|
| **Auth** | Mock IdP, user-picker login | Azure AD/Entra OIDC | Set `AUTH_PROVIDER=oidc` + configure OIDC env vars |
| **TLS** | Self-signed or HTTP | Real certificate | Configure Nginx with cert/key paths |
| **API Key** | Dev/test Claude key | Production Claude key | Set `ANTHROPIC_API_KEY` env var |
| **Content filter** | Default rules | Reviewed/expanded rules | Edit `config/content-filter.yaml` |
| **Domain** | localhost | chat.smithhoward.com | Update Nginx `server_name` and OIDC redirect URI |
| **Secrets** | `.env` file | Vault / K8s secrets | Swap env var source |
| **Monitoring** | None | Add logging, metrics | Add log aggregation, Prometheus endpoint |
| **Rate limiting** | None | Add Redis + rate limiter | Add Redis container, configure limits |
| **Logo** | Text mark | Actual S+H logo asset | Replace `logo.svg` in frontend assets |

### Production checklist (documented in README)

1. Register an OIDC application in Azure AD/Entra ID
2. Set `AUTH_PROVIDER=oidc` and configure OIDC env vars
3. Obtain and configure TLS certificate for the domain
4. Set production Claude API key
5. Review and expand content filter rules for your data
6. Set up DNS for the chat domain
7. Configure log aggregation
8. (Optional) Add Redis for rate limiting
9. (Optional) Add Prometheus metrics endpoint
10. Security review before go-live

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite |
| Reverse proxy | Nginx |
| Containerization | Docker, Docker Compose |
| LLM | Anthropic Claude API (anthropic Python SDK) |
| Auth (PoC) | PyJWT, mock IdP |
| Auth (prod) | authlib or python-jose, Azure AD OIDC |
| Content filter | Custom engine, PyYAML, openpyxl (Excel scanning) |
| Markdown | react-markdown, rehype-highlight |

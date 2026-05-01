# Data Handling & Security Guardrails

This document describes how Smith+Howard Chat handles sensitive financial data — what's protected, what's not, and what's needed for production.

## Principles

1. **No server-side storage** — conversations and files exist only in browser memory
2. **Scan before send** — every message and file is filtered before reaching the LLM
3. **Fail closed** — if the filter detects sensitive data, the request is blocked (not logged, not stored)
4. **Server-side enforcement** — the filter runs on the backend; it cannot be bypassed from the browser

## Data Flow

```
┌──────────┐     ┌──────────────┐     ┌────────────────┐     ┌─────────┐
│  User    │────▶│  FastAPI     │────▶│  Content       │────▶│  LLM    │
│  Browser │     │  Gateway     │     │  Filter        │     │  API    │
└──────────┘     └──────────────┘     └────────────────┘     └─────────┘
                        │                      │
                        │              ┌───────┴───────┐
                        │              │  BLOCK: 403   │
                        │              │  + reason     │
                        │              └───────────────┘
                        │
                   No disk writes
                   No database
                   No logs of content
```

## What Is Protected

### Text Message Scanning

| Pattern | Example | Detection Method | Action |
|---------|---------|-----------------|--------|
| UK National Insurance numbers | `AB123456C` | Regex: `[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]` | Block |
| Credit/debit card numbers | `4111111111111111` | Luhn algorithm (13-19 digits) | Block |
| UK bank account numbers | `12-34-56 12345678` | Regex: sort code + account pattern | Block |
| Email addresses | `john@example.com` | Standard email regex | Warn |

### File Upload Scanning

| File Type | Extraction Method | What Gets Scanned |
|-----------|------------------|-------------------|
| `.csv` | Python `csv.reader` | Every cell value |
| `.xlsx` | `openpyxl` library | Every cell in every worksheet |
| `.txt` | UTF-8 decode | Full file content |
| `.pdf` | UTF-8 decode (basic) | Raw text only — tables/formatted PDFs not fully extracted |
| `.png/.jpg` | Not scanned | Passed through to LLM without content analysis |

### File Type Allowlist

Only these extensions are accepted: `.csv`, `.xlsx`, `.pdf`, `.txt`, `.png`, `.jpg`

All other file types are rejected with a 400 error before any processing occurs.

## What Is NOT Protected (Known Gaps)

These are documented limitations of the PoC that should be addressed before handling real client data:

| Gap | Risk | Mitigation Path |
|-----|------|-----------------|
| **PDF text extraction is basic** | Formatted PDFs (tables, columns) won't be parsed correctly; sensitive data in PDF tables may not be detected | Add `pdfplumber` library for proper PDF parsing |
| **Images are not scanned** | Screenshots of spreadsheets containing NI numbers or card numbers will pass through | Add OCR (Tesseract) or rely on the LLM's vision capability for detection |
| **Pattern matching only** | Only catches data matching known regex patterns; novel formats or obfuscated data will pass | Add fuzzy matching, spacing-insensitive patterns |
| **No client name detection** | Client company names and individual names are not detected or blocked | Add configurable client-name blocklist |
| **No contextual awareness** | Column headers like "NI Number" or "Account" don't trigger blocks unless cell values match | Add column-header detection for sensitive field names |
| **Data still reaches external LLM** | After passing the filter, content is sent to OpenRouter/Anthropic servers | For maximum security, use on-premise LLM |

## Where Data Exists at Runtime

| Location | What | Lifetime |
|----------|------|----------|
| Browser `sessionStorage` | Conversation messages | Until tab is closed |
| FastAPI process memory | Uploaded file bytes (during request) | Milliseconds (single request lifecycle) |
| LLM provider servers | Message content + file text | Per provider's data retention policy |
| Server logs | Request metadata only (no content) | Configurable |

## Content Filter Configuration

Rules are defined in `config/content-filter.yaml` and loaded at startup.

### Adding a New Rule

```yaml
rules:
  # Block UK phone numbers
  - name: uk_phone_number
    pattern: '(\+44|0)\d{10,11}'
    action: block
    message: "Message blocked: contains what appears to be a UK phone number"

  # Block specific client names
  - name: client_names
    pattern: '(Acme Corp|Widget Inc|Example Ltd)'
    action: block
    message: "Message blocked: contains a client name"
```

### Rule Types

- **`pattern`** (regex) — matches text against a regular expression
- **`type: luhn`** — validates digit sequences using the Luhn algorithm (credit cards)

### Actions

- **`block`** — reject the request with 403 and show the message to the user
- **`warn`** — allow the request but notify the user (future: require confirmation)

## Recommendations for Production

Before handling real client financial data:

1. **Implement proper PDF extraction** — use `pdfplumber` for table parsing
2. **Add a client-name blocklist** — configurable list that blocks known client names
3. **Add column-header detection** — flag files with headers like "NI Number", "Account No"
4. **Add data masking** — option to redact sensitive values rather than blocking entire messages
5. **Audit logging** — record that uploads occurred (user, timestamp, pass/fail) without content
6. **Review LLM provider data policy** — understand how OpenRouter/Anthropic handle and retain data
7. **Consider on-premise LLM** — if client data cannot leave the corporate network
8. **Expand regex patterns** — add spacing-tolerant variants (e.g., `AB 123456 C`)
9. **Regular rule review** — schedule quarterly reviews of filter rules with compliance team

# Production Deployment Guide

This guide covers every step to move Smith+Howard Chat from the local PoC to a production deployment.

## Prerequisites

- A domain name (e.g., `chat.smithhoward.com`)
- Access to your corporate identity provider (Azure AD / Entra ID)
- A production Anthropic API key
- A TLS certificate for the domain
- A host to run Docker Compose (or equivalent container platform)

## Step 1: Register OIDC Application

1. Go to Azure Portal > Azure Active Directory > App registrations
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
# docker-compose.yml addition
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

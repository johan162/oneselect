# OneSelect Authentication Setup

This document provides a quick reference for setting up authentication in OneSelect.

## Quick Start

### 1. Install Dependencies

```bash
# Optional: If behind corporate proxy, configure PyPI source first
# poetry source add --priority=primary <name> <url>

poetry lock
poetry install
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required: JWT Settings
# Generate secret key
# openssl rand -hex 32
SECRET_KEY=generate-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Required: Database
SQLALCHEMY_DATABASE_URI=sqlite:///./oneselect.db

# Optional: Google OAuth
GOOGLE_CLIENT_ID=your-app-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000

# Optional: CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### 3. Run Database Migrations

```bash
poetry run alembic upgrade head
```

This will:
- Create the users table
- Add OAuth support fields (google_id, auth_provider)

### 4. Start the Server

```bash
poetry run uvicorn app.main:app --reload
```

## Authentication Methods

### Username/Password Login

Users can register and login with username/password:

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "user@example.com", "password": "pass123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=user&password=pass123"
```

### Google OAuth (Optional)

To enable Google OAuth:

1. **Set up Google Cloud Project** - See [docs/authentication.md](docs/authentication.md#setting-up-google-oauth)
2. **Add credentials to `.env`**
3. **Restart server**

Users can then login at: `http://localhost:8000/api/v1/auth/google/login`

## Default Admin Account

A superuser is created on first run:

- **Username:** `admin@example.com`
- **Password:** `admin`

⚠️ **Change this immediately in production!**

## Documentation

Full authentication documentation: [docs/authentication.md](docs/authentication.md)

Topics covered:
- Detailed API endpoints
- Google OAuth setup guide
- Account linking
- Security best practices
- Troubleshooting
- Admin access management

## Testing

Check if Google OAuth is configured:

```bash
curl http://localhost:8000/api/v1/auth/google/status
```

Response:
```json
{
  "google_oauth_enabled": true,
  "google_client_id_set": true,
  "google_client_secret_set": true
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login with username/password |
| `/api/v1/auth/change-password` | POST | Change password |
| `/api/v1/auth/google/login` | GET | Start Google OAuth flow |
| `/api/v1/auth/google/callback` | GET | Google OAuth callback |
| `/api/v1/auth/google/status` | GET | Check OAuth configuration |

## Troubleshooting

### Dependencies not installing

If you see pypi.org connection errors, try:
```bash
poetry lock
poetry install
```

### Migration errors

If migrations fail, check your database connection:
```bash
poetry run alembic current
poetry run alembic history
```

### Google OAuth not working

1. Verify credentials in `.env`
2. Check redirect URI matches Google Console
3. Ensure callback URL is accessible
4. Check server logs for errors

## Need Help?

See the complete guide: [docs/authentication.md](docs/authentication.md)

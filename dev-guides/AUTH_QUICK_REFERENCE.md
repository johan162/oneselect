# OneSelect Authentication - Quick Reference

## 🚀 Quick Setup (5 Minutes)

```bash
# 1. Install dependencies
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env: Set SECRET_KEY (use: openssl rand -hex 32)

# 3. Run migrations
poetry run alembic upgrade head

# 4. Start server
poetry run uvicorn app.main:app --reload
```

## 🔐 Authentication Methods

| Method | Endpoint | Use Case |
|--------|----------|----------|
| **Password** | `POST /api/v1/auth/login` | Traditional login |
| **Google OAuth** | `GET /api/v1/auth/google/login` | Social login (optional) |

## 📋 API Endpoints

### Password Authentication
```bash
# Register
POST /api/v1/auth/register
Body: {"username": "user", "email": "user@example.com", "password": "pass123"}

# Login
POST /api/v1/auth/login
Form: username=user&password=pass123

# Change Password
POST /api/v1/auth/change-password
Headers: Authorization: Bearer <token>
Body: {"current_password": "old", "new_password": "new"}
```

### Google OAuth (Optional)
```bash
# Check if enabled
GET /api/v1/auth/google/status

# Start OAuth flow (browser)
GET /api/v1/auth/google/login

# Callback (automatic)
GET /api/v1/auth/google/callback
```

## 🔑 Environment Variables

### Required
```bash
SECRET_KEY=your-secret-key-here
SQLALCHEMY_DATABASE_URI=sqlite:///./oneselect.db
```

### Optional (Google OAuth)
```bash
GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000
```

## 🎯 Google OAuth Setup

1. **Google Cloud Console:** https://console.cloud.google.com/
2. Create project → Enable Google+ API
3. OAuth consent screen → Create
4. Credentials → Create OAuth Client ID
5. Add redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
6. Copy Client ID & Secret to `.env`

**Full guide:** `docs/authentication.md#setting-up-google-oauth`

## 📦 Database Migration

```bash
# Apply migrations (adds OAuth fields)
poetry run alembic upgrade head

# Check current version
poetry run alembic current

# Rollback (if needed)
poetry run alembic downgrade -1
```

## 🧪 Testing

### Start Server
```bash
poetry run uvicorn app.main:app --reload
```

### Test Authentication

```bash
# Test password auth
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"test123"}'

# Test OAuth status
curl http://localhost:8000/api/v1/auth/google/status

# Test OAuth login (browser)
open http://localhost:8000/api/v1/auth/google/login
```

## 👤 Default Admin

**First run creates superuser:**
- Email: `admin@example.com`
- Password: `admin`

⚠️ **Change in production!**

## 🔒 Using Tokens

```bash
# Get token from login response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Make authenticated request
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me
```

### JavaScript Example
```javascript
// Store token
localStorage.setItem('token', token);

// Use in requests
fetch('/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
});
```

## 🐛 Troubleshooting

### OAuth not working?
```bash
# 1. Check configuration
curl http://localhost:8000/api/v1/auth/google/status

# 2. Verify redirect URI matches Google Console
# 3. Check .env file is loaded
# 4. Restart server after .env changes
```

### Login fails?
- OAuth users cannot login with password
- Check user exists: Look in database
- Verify password is correct
- Check user is active (`is_active=true`)

### Migration errors?
```bash
# Check current state
poetry run alembic current

# See migration history
poetry run alembic history

# Force to specific version
poetry run alembic upgrade a1b2c3d4e5f6
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `AUTHENTICATION_SETUP.md` | Quick setup guide |
| `docs/authentication.md` | Complete reference |
| `http://localhost:8000/docs` | Interactive API docs |
| `OAUTH_IMPLEMENTATION.md` | Implementation details |

## 🎨 User Flow Diagram

```
Password Auth:
  User → Register → DB → Login → JWT Token → API Access

Google OAuth:
  User → Google Login → Google Auth → Callback
      → Create/Link User → JWT Token → API Access
```

## 💡 Pro Tips

1. **Generate secure SECRET_KEY:** `openssl rand -hex 32`
2. **OAuth is optional:** App works without Google OAuth
3. **Account linking:** Same email = automatic link
4. **Token expiry:** 30 min default, adjust in `.env`
5. **CORS:** Add frontend URL to `BACKEND_CORS_ORIGINS`

## 🆘 Need Help?

1. Check `docs/authentication.md` (complete guide)
2. Review `AUTHENTICATION_SETUP.md` (setup steps)
3. See `OAUTH_IMPLEMENTATION.md` (technical details)
4. API Docs: http://localhost:8000/docs

---

**Quick Links:**
- Setup: `AUTHENTICATION_SETUP.md`
- Full Guide: `docs/authentication.md`
- Implementation: `OAUTH_IMPLEMENTATION.md`
- API Docs: http://localhost:8000/docs


## 📚 Documentation Guide

### For Quick Setup
→ **`AUTHENTICATION_SETUP.md`** (3-minute read)
- Installation steps
- Basic configuration
- Quick testing

### For Complete Reference
→ **`docs/authentication.md`** (15-minute read)
- Both authentication methods
- Google OAuth setup with screenshots
- Security best practices
- Troubleshooting
- API reference
- Admin access

### For Developers
→ **`AUTH_QUICK_REFERENCE.md`** (1-minute scan)
- Quick commands
- Common patterns
- Troubleshooting tips

→ **`OAUTH_IMPLEMENTATION.md`** (technical deep dive)
- Architecture decisions
- Database schema
- Security features
- Migration guide
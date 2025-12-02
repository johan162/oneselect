# Authentication Guide

OneSelect supports two authentication methods:

1. **Username/Password Authentication** - Traditional local authentication
2. **Google OAuth** - Sign in with your Google account

## Authentication Methods

### 1. Username/Password Authentication

Traditional authentication where users register with a username and password.

#### Registration

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_superuser": false,
  "auth_provider": "local"
}
```

#### Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body (Form Data):**
```
username=john_doe
password=SecurePassword123!
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Change Password

**Endpoint:** `POST /api/v1/auth/change-password`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword123!"
}
```

**Response:** `204 No Content`

---

### 2. Google OAuth Authentication

Sign in using your Google account. No password management required.

#### How It Works

1. User clicks "Sign in with Google" button
2. User is redirected to Google's login page
3. User authorizes the application
4. Google redirects back with user information
5. OneSelect creates/updates user account and issues JWT token

#### Integration Flow

**Step 1: Initiate OAuth Flow**

Direct users to: `GET /api/v1/auth/google/login`

This will redirect to Google's OAuth consent screen.

**Step 2: Handle Callback**

Google will redirect to: `GET /api/v1/auth/google/callback`

The backend will:
- Verify the Google token
- Create a new user account if one doesn't exist
- Link existing accounts by email
- Issue a JWT access token
- Redirect to frontend with token: `{FRONTEND_URL}/auth/callback?token=<jwt_token>`

#### Check OAuth Status

**Endpoint:** `GET /api/v1/auth/google/status`

**Response:**
```json
{
  "google_oauth_enabled": true,
  "google_client_id_set": true,
  "google_client_secret_set": true
}
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# JWT Settings
SECRET_KEY=your-secret-key-here-generate-with-openssl
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-app-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///./oneselect.db

# CORS Origins (comma-separated)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

### Generate Secret Key

```bash
openssl rand -hex 32
```

Copy the output to your `SECRET_KEY` environment variable.

---

## Setting Up Google OAuth

### Prerequisites

- Google Cloud Account
- Access to Google Cloud Console

### Step-by-Step Setup

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "OneSelect")
4. Click "Create"

#### 2. Enable Google+ API

1. In the Google Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for "Google+ API"
3. Click on it and click "Enable"

#### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type
3. Click "Create"
4. Fill in the required information:
   - **App name:** OneSelect
   - **User support email:** Your email
   - **Developer contact information:** Your email
5. Click "Save and Continue"
6. Skip "Scopes" section (click "Save and Continue")
7. Add test users (your email) if in testing mode
8. Click "Save and Continue"

#### 4. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Select "Web application"
4. Enter name: "OneSelect Backend"
5. Add **Authorized redirect URIs:**
   - Development: `http://localhost:8000/api/v1/auth/google/callback`
   - Production: `https://yourdomain.com/api/v1/auth/google/callback`
6. Click "Create"
7. **Copy the Client ID and Client Secret** - you'll need these!

#### 5. Update Environment Variables

Add to your `.env` file:

```bash
GOOGLE_CLIENT_ID=123456789-abcdefg.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_URL=http://localhost:3000
```

#### 6. Apply Database Migration

Run the migration to add OAuth fields to the User table:

```bash
poetry run alembic upgrade head
```

#### 7. Restart the Server

```bash
poetry run uvicorn app.main:app --reload
```

---

## User Model

Users in the system have the following attributes:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique user identifier |
| `username` | String | Unique username |
| `email` | String | User email (unique) |
| `hashed_password` | String | Hashed password (null for OAuth users) |
| `is_active` | Boolean | Account status |
| `is_superuser` | Boolean | Admin privileges |
| `role` | String | User role ("user" or "root") |
| `display_name` | String | Display name |
| `avatar_url` | String | Profile picture URL |
| `google_id` | String | Google user ID (OAuth) |
| `auth_provider` | String | "local" or "google" |

---

## Account Linking

If a user with the same email exists:

- **Local account exists** → Google OAuth will link the account and update `google_id`
- **Google account exists** → Cannot link another provider
- **No account exists** → New account is created

---

## Making Authenticated Requests

After login (either method), include the JWT token in requests:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/v1/users/me
```

### Frontend Example (JavaScript)

```javascript
// Store token after login
localStorage.setItem('access_token', token);

// Make authenticated request
fetch('http://localhost:8000/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## Admin Access

### Creating the First Superuser

The first superuser (admin) is automatically created when the application starts:

**Default Credentials:**
- Username: `admin@example.com`
- Password: `admin`

⚠️ **Change these immediately in production!**

### Manually Creating a Superuser

Use the database directly or create an endpoint to promote users:

```sql
UPDATE users 
SET is_superuser = 1, role = 'root' 
WHERE username = 'desired_admin_username';
```

### Checking User Permissions

```python
from app.api.deps import get_current_active_superuser

@router.get("/admin-only")
def admin_route(
    current_user: User = Depends(get_current_active_superuser)
):
    # Only accessible by superusers
    return {"message": "Admin access granted"}
```

---

## Security Best Practices

### 1. Production Configuration

- **Change `SECRET_KEY`** - Generate a new one for production
- **Use HTTPS** - Always use SSL/TLS in production
- **Secure CORS** - Limit `BACKEND_CORS_ORIGINS` to your frontend domain
- **Change default admin password** immediately

### 2. Password Requirements

Passwords must:
- Be at least 8 characters long (recommended: 12+)
- Include uppercase and lowercase letters
- Include numbers
- Include special characters

### 3. Token Expiration

Tokens expire after 30 minutes by default. Adjust via:

```bash
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4. Rate Limiting

Consider implementing rate limiting for login endpoints to prevent brute force attacks.

---

## Troubleshooting

### Google OAuth Not Working

**Check Configuration:**

```bash
curl http://localhost:8000/api/v1/auth/google/status
```

**Common Issues:**

1. **Invalid redirect URI**
   - Ensure redirect URI in Google Console matches exactly
   - Include port number (e.g., `:8000`)

2. **Client ID/Secret not set**
   - Verify `.env` file is loaded
   - Check environment variables are set correctly

3. **CORS errors**
   - Add frontend URL to `BACKEND_CORS_ORIGINS`

### Login Failures

1. **"Incorrect email or password"**
   - Verify credentials
   - Check user exists in database
   - OAuth users cannot login with password

2. **"Inactive user"**
   - User account is disabled
   - Check `is_active` field in database

3. **Token expired**
   - Request a new token by logging in again
   - Implement refresh token logic if needed

---

## Testing Authentication

### Test Username/Password Login

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=TestPass123!"
```

### Test Google OAuth

1. Start the server: `poetry run uvicorn app.main:app --reload`
2. Visit: `http://localhost:8000/api/v1/auth/google/login`
3. Login with your Google account
4. You'll be redirected to frontend with token

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login with username/password | No |
| POST | `/api/v1/auth/change-password` | Change password | Yes |
| GET | `/api/v1/auth/google/login` | Initiate Google OAuth | No |
| GET | `/api/v1/auth/google/callback` | Google OAuth callback | No |
| GET | `/api/v1/auth/google/status` | Check OAuth config | No |
| POST | `/api/v1/auth/login/test-token` | Verify token | Yes |

---

## Migration Guide

### Existing Installations

If you have an existing installation, follow these steps:

1. **Backup your database**
   ```bash
   cp oneselect.db oneselect.db.backup
   ```

2. **Update dependencies**
   ```bash
   poetry lock
   poetry install
   ```

3. **Run migrations**
   ```bash
   poetry run alembic upgrade head
   ```

4. **Add OAuth configuration** (optional)
   - Add Google OAuth credentials to `.env`
   - Restart the server

Existing users with passwords will continue to work. They can also link their Google account by logging in with Google using the same email.

---

## Support

For issues or questions:
- GitHub: [https://github.com/johan162/oneselect](https://github.com/johan162/oneselect)
- Documentation: [https://johan162.github.io/oneselect](https://johan162.github.io/oneselect)

# Working Behind Corporate Proxies

This guide helps developers working behind corporate proxies or using PyPI mirrors/caches.

## Poetry with Custom PyPI Sources

If your organization uses a PyPI mirror (Artifactory, Nexus, etc.), configure Poetry to use it:

### Add Custom Source

```bash
poetry source add --priority=primary <source-name> <source-url>
```

**Example with Artifactory:**
```bash
poetry source add --priority=primary artifactory \
  https://your-artifactory.com/artifactory/api/pypi/pypi-virtual/simple
```

**Example with Nexus:**
```bash
poetry source add --priority=primary nexus \
  https://your-nexus.com/repository/pypi-proxy/simple
```

### Verify Configuration

```bash
poetry source show
```

### Set Proxy Environment Variables

If you need an HTTP proxy:

```bash
export https_proxy=http://proxy.company.com:8080
export http_proxy=http://proxy.company.com:8080
```

Add to `~/.zshrc` or `~/.bashrc` to make permanent:
```bash
echo 'export https_proxy=http://proxy.company.com:8080' >> ~/.zshrc
echo 'export http_proxy=http://proxy.company.com:8080' >> ~/.zshrc
source ~/.zshrc
```

## Configuration Persistence

Your Poetry source configuration is stored in:
- **Project-level**: `pyproject.toml` (not recommended for company-specific URLs)
- **User-level**: `~/.config/pypoetry/config.toml` (recommended)

The `poetry source add` command stores configuration at the **project level** by default, adding it to `pyproject.toml`. 

To keep company-specific URLs out of the repository, you have two options:

### Option 1: Manual Configuration (Recommended)
Each developer runs the `poetry source add` command locally. The source is added to `pyproject.toml` but should be in `.gitignore` or manually excluded from commits.

### Option 2: Global Poetry Configuration
Configure default sources globally:

```bash
# Edit Poetry's global config
poetry config repositories.artifactory https://your-artifactory.com/...
poetry config http-basic.artifactory <username> <password>
```

Or manually edit `~/.config/pypoetry/config.toml`:

```toml
# ~/.config/pypoetry/config.toml

[repositories.artifactory]
url = "https://your-artifactory.com/artifactory/api/pypi/mme-pypi-virtual/simple"

[http-basic.artifactory]
username = "your-username"
password = "your-password"

# Optional: Set as default source
[installer]
parallel = true

[virtualenvs]
in-project = true
```

After editing, verify with:
```bash
poetry config --list
```

## Using pip's Configuration

Poetry doesn't automatically read pip's configuration (`~/.pip/pip.conf`). If you have pip configured, you must separately configure Poetry as shown above.

## Troubleshooting

### Poetry can't connect to PyPI

**Symptom:** `All attempts to connect to pypi.org failed`

**Solution:**
1. Verify proxy environment variables are set
2. Add your PyPI mirror as primary source
3. Test with `poetry lock -vv` to see connection attempts

### Certificate Errors

**Symptom:** SSL certificate verification failed

**Solution:**
```bash
# Disable SSL verification (not recommended for production)
poetry config certificates.<source-name>.cert false

# Or provide custom CA bundle
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
```

### Authentication Required

If your PyPI mirror requires authentication:

```bash
poetry config http-basic.<source-name> <username> <password>

# Or use tokens
poetry config pypi-token.<source-name> <token>
```

## .gitignore Entry

To prevent accidental commits of source configuration, ensure your `.gitignore` includes:

```
# Poetry source configuration (company-specific)
# Remove [[tool.poetry.source]] sections before committing if added
```

Or manually review `pyproject.toml` before committing to ensure no company-specific URLs are included.

## Example Workflow

```bash
# 1. Clone repository
git clone https://github.com/johan162/oneselect.git
cd oneselect

# 2. Configure proxy (if needed)
export https_proxy=http://localhost:9000

# 3. Add PyPI mirror (if needed)
poetry source add --priority=primary artifactory \
  https://your-mirror.com/api/pypi/pypi-virtual/simple

# 4. Lock and install dependencies
poetry lock
poetry install

# 5. Before committing changes to pyproject.toml
# Remove any [[tool.poetry.source]] sections that were added
```

## CI/CD Considerations

For CI/CD pipelines that run outside your corporate network:
- Use environment variables for proxy configuration
- Don't commit source URLs to the repository
- Configure CI/CD to use public PyPI
- Or maintain separate `pyproject.toml` for internal/external builds

---

**Note:** This guide is for development setup only. The OneSelect application itself does not require any special proxy configuration at runtime.

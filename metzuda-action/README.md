# Metzuda GitHub Action

GitHub Action to integrate the Metzuda security scanner into your CI/CD pipelines.

Metzuda scans your workspace for security vulnerabilities commonly introduced by AI coding assistants (such as hardcoded secrets, SQL injections, insecure CORS configurations, dynamic code evaluation, and IDOR/broken access controls).

---

## Usage Examples

### 1. Basic Usage (Fast local scan, no AI API cost)
Perfect for run-on-push checks or fast PR validations without requiring an Anthropic API key.

```yaml
name: Metzuda Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Metzuda
        uses: rfmota/metzuda-action@v1
        with:
          no-ai: true
          fail-on: HIGH
```

### 2. Full Usage (With Layer 2 AI Semantic Analysis)
Uses the Anthropic Claude API to perform deep semantic checks for IDOR and logical authorization bypasses on severe static analysis findings.

```yaml
name: Metzuda Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Metzuda
        uses: rfmota/metzuda-action@v1
        with:
          no-ai: false
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          fail-on: HIGH
```

### 3. Lenient Mode (Fail on CRITICAL findings only)
Allows warnings and high-severity findings to pass, only blocking the build if a `CRITICAL` vulnerability is identified.

```yaml
name: Metzuda Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run Metzuda
        uses: rfmota/metzuda-action@v1
        with:
          no-ai: true
          fail-on: CRITICAL
```

---

## GitHub Security Tab Integration

By default, this action generates and uploads a standard SARIF v2.1.0 report. This unlocks inline security alerts directly inside your pull request reviews and files diffs under the GitHub **Security** tab.

**Pull Request Review Example:**
If an AI coding assistant introduces a hardcoded database password or Stripe token, the Metzuda action will block the PR and attach an inline comment on the exact line of code:
> **Metzuda Security Alert: HARDCODED_SECRET**
> 
> * **Severity**: HIGH
> * **File**: `src/config/db.js` (Line 15)
> * **Message**: Do not hardcode raw credentials in configuration files. Retrieve them via environment variables instead.

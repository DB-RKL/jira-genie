# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue for security-sensitive findings.
2. Email the repository maintainer with a description of the issue, steps to reproduce, and potential impact.
3. Allow reasonable time for a fix before public disclosure.

## Scope

This repository contains Databricks Asset Bundle configuration, data transformation code, and generated analytics artifacts. It does not store credentials — customers configure their own `config/pipeline.yaml` locally (gitignored).

## Best Practices for Deployers

- Never commit `config/pipeline.yaml` with real warehouse IDs or personal emails to a public fork
- Use workspace secrets or environment variables for sensitive values in CI/CD
- Restrict Unity Catalog permissions to least privilege

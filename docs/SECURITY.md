# Security Policy

## Vulnerability Scanning

We take security seriously and run automated vulnerability scans on every build using [Trivy](https://github.com/aquasecurity/trivy).

- **Automated Scanning:** Every pull request and push to main is scanned.
- **Reporting:** Results are uploaded to the GitHub Security tab.
- **Policy:** We focus on actionable, fixable vulnerabilities.

## Base OS Vulnerabilities

This project uses a minimal Docker image based on Debian.

You may see vulnerabilities reported in system packages. These are:
1. **Upstream Issues:** Vulnerabilities in the base OS packages.
2. **Often Unfixable:** Many have no fix available in the current stable release.
3. **Low Risk:** Our container runs as a non-root user with limited privileges and no exposed ports.

**Our Strategy:**
- We ignore "unfixed" vulnerabilities in CI/CD to prevent blocking development.
- We monitor for security updates and rebuild our images regularly.
- We prioritize fixing vulnerabilities in our application code and Python dependencies.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately.

**Do not open a public issue.**

Instead, please email [your-email@example.com] or open a GitHub Security Advisory draft if you have permissions.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |
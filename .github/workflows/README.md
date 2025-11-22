# CI/CD Workflows

This directory contains the GitHub Actions workflows for the web-to-openwebui project.

## Pipeline Architecture

The pipeline is designed with a **three-tier optimization strategy** to balance feedback speed with validation depth.

---

## Workflow Overview

```mermaid
graph TB
    subgraph "Event Triggers"
        PR[Pull Request]
        MAIN[Push to Main]
        TAG[Tag v*]
    end
    
    subgraph "Jobs"
        LINT[Lint Job]
        TEST[Test Job]
        DOCKER[Docker Job]
        RELEASE[Release Job]
    end
    
    PR --> LINT
    MAIN --> LINT
    TAG --> LINT
    
    LINT --> TEST
    TEST --> DOCKER
    DOCKER -.-> RELEASE
    
    TAG -.Only on tags.-> RELEASE
    
    style PR fill:#e3f2fd,stroke:#1976d2
    style MAIN fill:#fff3e0,stroke:#f57c00
    style TAG fill:#f3e5f5,stroke:#7b1fa2
    style LINT fill:#e8f5e9,stroke:#388e3c
    style TEST fill:#e8f5e9,stroke:#388e3c
    style DOCKER fill:#fff9c4,stroke:#fbc02d
    style RELEASE fill:#ffebee,stroke:#c62828
```

---

## 1. Pull Request Workflow (Fast Feedback)

**Trigger:** Open/Sync PR to main

**Goal:** Quick validation for developers. Skips expensive operations.

```mermaid
graph TB
    subgraph "Lint Job"
        L1[Checkout Code] --> L2[Setup Python 3.11]
        L2 --> L3[Install Dev Dependencies]
        L3 --> L4[Ruff Check]
        L4 --> L5[Black Format Check]
        L5 --> L6[Mypy Type Check]
    end
    
    subgraph "Test Job"
        T1[Checkout Code] --> T2[Setup Python 3.11]
        T2 --> T3[Install Dependencies]
        T3 --> T4[Install Playwright]
        T4 --> T5[Run Unit Tests]
        T5 --> T6[Upload Coverage]
        T6 --> T7[Comment PR]
    end
    
    subgraph "Docker Job"
        D1[Checkout Code] --> D2[Setup Buildx]
        D2 --> D3[Extract Metadata]
        D3 --> D4[Hadolint Dockerfile]
        D4 --> D5[Build Single-Arch<br/>linux/amd64]
        D5 --> D6{PR Event?}
        D6 -->|Yes| D7[Skip Security Scan]
        D6 -->|No| D8[Skip - Not PR]
    end
    
    L6 --> T1
    T7 --> D1
    
    style L4 fill:#e8f5e9,stroke:#388e3c
    style L5 fill:#e8f5e9,stroke:#388e3c
    style L6 fill:#e8f5e9,stroke:#388e3c
    style T5 fill:#e3f2fd,stroke:#1976d2
    style T7 fill:#e3f2fd,stroke:#1976d2
    style D5 fill:#fff9c4,stroke:#f57c00
    style D7 fill:#ffebee,stroke:#e57373
```

**What Runs:**
- ✅ Python linting (Ruff, Black, Mypy)
- ✅ Unit tests with coverage reporting
- ✅ Docker build validation (single-arch amd64)
- ✅ Hadolint Dockerfile linting

**What's Skipped:**
- ❌ Security scanning (too slow for PR feedback)
- ❌ Multi-arch builds
- ❌ Push to registry

**Estimated Duration:** ~6 minutes

---

## 2. Push to Main Workflow (Full Validation)

**Trigger:** Merge/Push to main branch

**Goal:** Ensure the codebase is secure and stable before release.

```mermaid
graph TB
    subgraph "Lint & Test"
        LT[Same as PR Workflow]
    end
    
    subgraph "Docker Job - Main Branch"
        D1[Checkout Code] --> D2[Setup QEMU & Buildx]
        D2 --> D3[Login to GHCR]
        D3 --> D4[Extract Metadata]
        D4 --> D5[Hadolint]
        D5 --> D6[Build Single-Arch<br/>linux/amd64<br/>Load to Local]
        D6 --> D7{Main Branch?}
        D7 -->|Yes| D8[Security Scan<br/>Local Image]
        D8 --> D9[Upload SARIF to<br/>GitHub Security]
        D9 --> D10[Display Table Summary]
        D10 --> D11[End - No Push]
    end
    
    LT --> D1
    
    style D6 fill:#e1f5fe,stroke:#01579b
    style D8 fill:#fff9c4,stroke:#f57c00
    style D9 fill:#ffebee,stroke:#c62828
    style D10 fill:#fff9c4,stroke:#fbc02d
    style D11 fill:#e8f5e9,stroke:#388e3c
```

**What Runs:**
- ✅ Complete lint & test suite
- ✅ Docker build (single-arch amd64, loaded locally)
- ✅ Trivy security scan (CRITICAL/HIGH/MEDIUM)
- ✅ Upload SARIF to GitHub Security tab
- ✅ Console security summary

**What's Skipped:**
- ❌ Multi-arch builds (we only release on tags)
- ❌ Push to registry (main doesn't publish)

**Estimated Duration:** ~10 minutes

---

## 3. Tag Release Workflow (Production Deployment)

**Trigger:** Push tag `v*` (e.g., v1.0.0, v1.2.3-beta)

**Goal:** Secure production release. Pre-flight scan prevents publishing vulnerable images.

```mermaid
graph TB
    subgraph "Lint & Test"
        LT[Same as PR Workflow]
    end
    
    subgraph "Docker Job - Tag Release"
        D1[Checkout Code] --> D2[Setup QEMU & Buildx]
        D2 --> D3[Login to GHCR]
        D3 --> D4[Extract Metadata]
        D4 --> D5[Hadolint]
        D5 --> D6{Tag Event?}
        D6 -->|Yes| D7[Build Single-Arch<br/>linux/amd64<br/>Load Locally]
        D7 --> D8[Security Scan<br/>Local Image]
        D8 -->|PASS| D9[Build Multi-Arch<br/>linux/amd64<br/>linux/arm64]
        D9 --> D10[Push to GHCR]
        D10 --> D11[Generate SBOM &<br/>Provenance]
        D11 --> D12[Upload SARIF]
        D12 --> D13[Display Summary]
        D8 -->|FAIL| D14[STOP:<br/>Don't Publish]
    end
    
    subgraph "Release Job"
        R1[Checkout Code] --> R2[Extract Version]
        R2 --> R3[Extract Changelog]
        R3 --> R4{Pre-release?}
        R4 -->|alpha/beta/rc| R5[Create Pre-Release]
        R4 -->|stable| R6[Create Release]
        R5 --> R7[Add Docker Info]
        R6 --> R7
    end
    
    LT --> D1
    D13 --> R1
    
    style D7 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    style D8 fill:#e1f5fe,stroke:#01579b
    style D9 fill:#ffccbc,stroke:#bf360c
    style D10 fill:#fff9c4,stroke:#fbc02d
    style D11 fill:#fff9c4,stroke:#f57c00
    style R5 fill:#ffebee,stroke:#c62828
    style R6 fill:#e8f5e9,stroke:#2e7d32
```

**Key Security Feature:** Pre-flight scan prevents publishing vulnerable images!

**What Runs:**
- ✅ Complete lint & test suite
- ✅ **Pre-flight Build** (linux/amd64) - Local scan target
- ✅ **Security Scan** (local image) - Quality gate
- ✅ **Multi-arch build** (linux/amd64, linux/arm64) - Only if scan passes
- ✅ Push to GitHub Container Registry
- ✅ Generate SBOM and provenance attestations
- ✅ Upload SARIF to GitHub Security tab
- ✅ Create GitHub Release with auto-extracted changelog
- ✅ Detect pre-release tags (alpha/beta/rc)

**Security Benefit:** Vulnerable images are never published - scan happens BEFORE push.

**Estimated Duration:** ~12 minutes (pre-flight scan adds ~2 min, prevents bad releases)

---

## Conditional Logic Summary

| Condition | Lint | Test | Build Type | Security Scan | Push Registry | Release |
|-----------|------|------|------------|---------------|---------------|---------|
| **Pull Request** | ✅ | ✅ | Single-arch | ❌ | ❌ | ❌ |
| **Push to Main** | ✅ | ✅ | Single-arch | ✅ Local (CRITICAL only) | ❌ | ❌ |
| **Tag v*** | ✅ | ✅ | Single + Multi | ✅ **Pre-flight** (before push) | ✅ | ✅ |

---

## Key Optimizations

### 1. Pre-flight Security Scanning
- **Strategy:** Build → Scan → Push (not Push → Scan)
- **Benefit:** Vulnerable images never reach the registry
- **Tag Releases:** Single-arch build → Scan → Multi-arch build & push
- **Trade-off:** +2 minutes per release, but ensures security

### 2. Smart Security Scanning
- **PRs:** Skipped (fast feedback loop)
- **Main:** Scans local build (CRITICAL-only quality gate)
- **Tags:** Pre-flight scan

### 3. Aggressive Caching
- **Pip dependencies:** GitHub Actions cache
- **Docker layers:** GitHub Actions cache with `mode=max`
- **Playwright browsers:** Cached by actions/setup-python

### 4. Parallel Where Possible
- Lint job can start immediately
- Test job waits for lint (fail-fast)
- Docker job waits for both (avoid wasted builds)

---

## Security Scanning Details

### Trivy Configuration (v0.33.1)

**Scan Strategy - Pre-flight Security Gates**

**Quality Gates (Block Releases):**

**Main Branch:**
- Scans local build before merging to main
- Blocks ONLY on **CRITICAL** vulnerabilities
- HIGH/MEDIUM tracked but non-blocking

**Tag Release (Pre-flight):**
- Builds single-arch image (`linux/amd64`) locally

**Configuration:**
- **Scanners:** `vuln` only (vulnerabilities, not secrets)
- **Severity:** CRITICAL, HIGH, MEDIUM (all tracked in SARIF)
- **Blocking:** CRITICAL only (`exit-code: '1'`)
- **Ignore Unfixed:** `true` (don't fail on upstream/unpatchable issues)
- **SARIF Filtering:** `limit-severities-for-sarif: true` (required for severity to work)

**Outputs:**
1. **SARIF:** Uploaded to GitHub Security tab for all severities
2. **Table:** Console summary in workflow logs

**Best Practice:** Monitor GitHub Security tab regularly. Address CRITICAL immediately. Plan upgrades for HIGH when upstream patches available.

---

## Release Automation

### Changelog Integration

The workflow attempts to extract release notes from `CHANGELOG.md`:

```markdown
## [1.2.3] - 2024-01-15
- Feature: Added new thing
- Fix: Fixed bug

## [1.2.2] - 2024-01-10
...
```

If the version is missing from changelog, a default message is used.

### Pre-release Detection

Tags matching `-(alpha|beta|rc)` are automatically marked as pre-releases:
- `v1.0.0-alpha.1` → Pre-release ✅
- `v1.0.0-beta` → Pre-release ✅
- `v1.0.0` → Stable release

### Docker Image Tags

A release `v1.2.3` creates:
- `ghcr.io/owner/repo:v1.2.3`
- `ghcr.io/owner/repo:1.2`
- `ghcr.io/owner/repo:1`
- `ghcr.io/owner/repo:latest` (if default branch)

---

## Workflow Files

- **`ci-cd.yml`:** Main pipeline (this document describes it)
- **Future:** Separate scheduled security scanning workflow (optional)
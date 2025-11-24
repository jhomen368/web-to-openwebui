# Kubernetes Deployment Guide

This guide explains how to deploy `web-to-openwebui` to a Kubernetes cluster. The application is designed to be Kubernetes-friendly, using a single persistent volume for data and ConfigMaps for site configurations.

## Prerequisites

*   **Kubernetes Cluster**: A running cluster (v1.24+ recommended).
*   **kubectl**: Configured to communicate with your cluster.
*   **OpenWebUI**: A running instance of OpenWebUI reachable from the cluster.
*   **Storage Class**: A default storage class for Persistent Volume Claims (PVCs).

## Deployment Strategy

We use a **Single Mount Architecture**:
*   **One PVC (`/app/data`)**: Stores all persistent data (outputs, logs, and dynamic config).
*   **ConfigMap Mounts**: Site configurations are mounted from ConfigMaps into `/app/data/config/sites/`.

## Manifest Examples

Save these manifests to a file (e.g., `webowui.yaml`) or apply them individually.

### 1. Namespace

Create a dedicated namespace for isolation.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: web-to-openwebui
```

### 2. Secret (Credentials)

Store sensitive API keys securely.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: webowui-creds
  namespace: web-to-openwebui
type: Opaque
stringData:
  OPENWEBUI_API_KEY: "sk-your-api-key-here"
```

### 3. Persistent Volume Claim (Storage)

Request storage for scraped data and logs.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: webowui-data
  namespace: web-to-openwebui
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn # Replace with your storage class (e.g., standard, local-path)
  resources:
    requests:
      storage: 10Gi
```

### 4. ConfigMap (Site Configurations)

Defines the sites to scrape. These files will be mounted into the configuration directory. Update this section to match your desired configuration the below configuration is shown to show an example of tested configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webowui-sites
  namespace: web-to-openwebui
data:
  monsterhunter.yaml: |
    site:
      name: "monsterhunter"
      display_name: "Monster Hunter Wiki"
      base_url: "https://monsterhunterwiki.org"
      start_urls:
        - "https://monsterhunterwiki.org/wiki/Main_Page"

    crawling:
      strategy: "bfs"
      max_depth: 1
      max_pages: null
      streaming: false
      filters:
        follow_patterns:
          - "^https://monsterhunterwiki\\.org/wiki/.*"
        exclude_patterns:
          - ".*Special:.*"
          - ".*User:.*"
          - ".*Talk:.*"
          - ".*File:.*"
          - ".*Template:.*"
          - ".*Category:.*"
          - ".*Help:.*"
          - ".*action=edit.*"
          - ".*action=history.*"

          # Wiki administrative/meta pages
          - ".*[Ww]iki:[Aa]bout"
          - ".*[Ww]iki:.*[Dd]isclaimer"
          - ".*[Ww]iki:[Cc]opyrights?"
          - ".*[Ww]iki:[Pp]rivacy"
          - ".*[Ww]iki:[Cc]ommunity"

          # Edit/action pages and redirects
          - ".*/edit(\\?.*)?$"
          - ".*&action=(edit|history|delete|protect)"
          - ".*\\?redlink="

          # Version history and changelog pages
          - ".*[Vv]ersion.*[Hh]istory"
          - ".*[Cc]hangelog"
          - ".*[Pp]atch.*[Nn]otes"

          # Image and file description pages
          - ".*Image:.*"
      rate_limit:
        requests_per_second: 1
        delay_between_requests: 1.0
        max_retries: 3

    html_filtering:
      excluded_tags:
        - nav
        - footer
        - aside
        - header
      exclude_external_links: true
      exclude_social_media_links: true
      min_block_words: 10

      pruning:
        enabled: false
        threshold: 0.55
        min_words: 50

    markdown_conversion:
      content_selector: "body"
      remove_selectors:
        - "script"
        - "style"
        - "nav"
        - "footer"
        - ".mw-navigation"
        - ".mw-footer"
        - ".toc"
      markdown_options:
        include_images: true
        include_links: true
        preserve_structure: true
        heading_style: "atx"

    result_filtering:
      min_page_length: 50
      max_page_length: 500000
      allowed_content_types:
        - "text/html"
      filter_dead_links: true

    markdown_cleaning:
      profile: "mediawiki"

    openwebui:
      knowledge_name: "Monster Hunter"
      description: "Comprehensive Monster Hunter game mechanics, monsters, weapons, armor, and equipment database"
      auto_upload: true
      batch_size: 10
      preserve_deleted_files: false
      auto_rebuild_state: true
      rebuild_confidence_threshold: "medium"

    retention:
      enabled: true
      keep_backups: 2
      auto_cleanup: true

    schedule:
      enabled: true
      type: "cron"
      cron: "0 3 * * *"
      timezone: "America/Los_Angeles"
      timeout_minutes: 60
      retry:
        enabled: true
        max_attempts: 3
        delay_minutes: 15

  poe2wiki.yaml: |
    site:
      name: "poe2wiki"
      display_name: "Path of Exile 2 Wiki"
      base_url: "https://www.poe2wiki.net"
      start_urls:
        - "https://www.poe2wiki.net/wiki/Path_of_Exile_2_Wiki"

    crawling:
      strategy: "bfs"
      max_depth: 1
      max_pages: null
      streaming: false
      filters:
        follow_patterns:
          - "^https://www\\.poe2wiki\\.net/wiki/.*"
        exclude_patterns:
          - ".*Special:.*"
          - ".*User:.*"
          - ".*Talk:.*"
          - ".*File:.*"
          - ".*Template:.*"
          - ".*Category:.*"
          - ".*Help:.*"
          - ".*action=edit.*"
          - ".*action=history.*"

          # Wiki administrative/meta pages
          - ".*[Ww]iki:[Aa]bout"
          - ".*[Ww]iki:.*[Dd]isclaimer"
          - ".*[Ww]iki:[Cc]opyrights?"
          - ".*[Ww]iki:[Pp]rivacy"
          - ".*[Ww]iki:[Cc]ommunity"

          # Edit/action pages and redirects
          - ".*/edit(\\?.*)?$"
          - ".*&action=(edit|history|delete|protect)"
          - ".*\\?redlink="

          # Version history and changelog pages
          - ".*[Vv]ersion.*[Hh]istory"
          - ".*[Cc]hangelog"
          - ".*[Pp]atch.*[Nn]otes"

          # Image and file description pages
          - ".*Image:.*"
      rate_limit:
        requests_per_second: 1
        delay_between_requests: 1.0
        max_retries: 3

    html_filtering:
      excluded_tags:
        - nav
        - footer
        - aside
        - header
      exclude_external_links: true
      exclude_social_media_links: true
      min_block_words: 10

      pruning:
        enabled: false
        threshold: 0.55
        min_words: 50

    markdown_conversion:
      content_selector: "body"
      remove_selectors:
        - "script"
        - "style"
        - "nav"
        - "footer"
        - ".mw-navigation"
        - ".mw-footer"
        - ".toc"
      options:
        include_images: true
        include_links: true
        preserve_structure: true
        heading_style: "atx"

    result_filtering:
      min_page_length: 50
      max_page_length: 500000
      allowed_content_types:
        - "text/html"

    markdown_cleaning:
      profile: "mediawiki"
      # config:
      #   filter_dead_links: true
      #   remove_citations: true
      #   remove_categories: true
      #   remove_media: true
      #   remove_references_section: true
      #   remove_header_navigation: true

    openwebui:
      knowledge_name: "Path of Exile 2"
      description: "Path of Exile 2 game mechanics, character classes, skills, items, and endgame content"
      auto_upload: true
      batch_size: 10
      preserve_deleted_files: false
      auto_rebuild_state: true
      rebuild_confidence_threshold: "medium"

    retention:
      enabled: true
      keep_backups: 2
      auto_cleanup: true

    schedule:
      enabled: true
      type: "cron"
      cron: "0 2 * * *"
      timezone: "America/Los_Angeles"
      timeout_minutes: 60
      retry:
        enabled: true
        max_attempts: 3
        delay_minutes: 15
```

👉 **For full configuration options, see:** [`webowui/config/examples/README.md`](../webowui/config/examples/README.md)

### 5. Deployment

Runs the webowui daemon.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-to-openwebui
  namespace: web-to-openwebui
  labels:
    app: web-to-openwebui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web-to-openwebui
  template:
    metadata:
      labels:
        app: web-to-openwebui
    spec:
      containers:
        - name: web-to-openwebui
          image: ghcr.io/jhomen368/web-to-openwebui:latest
          imagePullPolicy: Always
          env:
            - name: OPENWEBUI_BASE_URL
              value: "http://open-webui.default.svc.cluster.local:8080" # Update with your service URL
            - name: OPENWEBUI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: webowui-creds
                  key: OPENWEBUI_API_KEY
            - name: TZ
              value: "America/Los_Angeles"
          volumeMounts:
            - name: data
              mountPath: /app/data
            - name: config
              mountPath: /app/data/config/sites/monsterhunter.yaml
              subPath: monsterhunter.yaml
            - name: config
              mountPath: /app/data/config/sites/poe2wiki.yaml
              subPath: poe2wiki.yaml
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: webowui-data
        - name: config
          configMap:
            name: webowui-sites
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENWEBUI_BASE_URL` | URL of your OpenWebUI instance | Required |
| `OPENWEBUI_API_KEY` | API Key for OpenWebUI | Required |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | INFO |
| `TZ` | Timezone for scheduler | America/Los_Angeles |

### Understanding the subPath Mount Strategy

You'll notice in the Deployment example that each site config file is mounted individually using `subPath`. This isn't just a preference - it's actually required to prevent permission issues.

Here's what happens if you mount the ConfigMap to the entire directory:
- Kubernetes makes `/app/data/config/sites/` completely read-only
- The application tries to copy example template files during startup
- It crashes with "Permission denied" errors

By mounting each file individually with `subPath`, you get the best of both worlds:
- Your site configs stay read-only and managed via GitOps (the ConfigMap files)
- The directory itself remains writable for template files and other dynamic content
- No security contexts or init containers required - it just works

### Adding New Sites

When you're ready to add another site to scrape:

1. **Update the ConfigMap** with your new site's configuration:
   ```bash
   kubectl edit configmap/webowui-sites -n web-to-openwebui
   ```

2. **Add a volumeMount** for the new file in your Deployment:
   ```yaml
   volumeMounts:
     # ... your existing mounts ...
     - name: config
       mountPath: /app/data/config/sites/mynewsite.yaml
       subPath: mynewsite.yaml  # Don't forget the subPath!
   ```

3. **Apply and restart** to pick up the changes:
   ```bash
   kubectl apply -f webowui.yaml
   kubectl rollout restart deployment/web-to-openwebui -n web-to-openwebui
   ```

The scheduler will automatically discover the new site and start scraping according to its configured schedule.

## Troubleshooting

**Pod crashes with "Permission denied" or "Read-only file system" errors:**

Check your volumeMounts - if you mounted the ConfigMap directly to `/app/data/config/sites` without using `subPath`, that's your problem. Each site config needs its own volumeMount entry with `subPath` specified. See the Deployment example above.

**ConfigMap changes aren't showing up in the pod:**

ConfigMaps are read when the pod starts, not dynamically. After updating your ConfigMap, restart the deployment:
```bash
kubectl rollout restart deployment/web-to-openwebui -n web-to-openwebui

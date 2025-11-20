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

Defines the sites to scrape. These files will be mounted into the configuration directory.

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
      
    strategy:
      type: "recursive"
      max_depth: 1
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
        # ... (add more patterns as needed)
      rate_limit:
        requests_per_second: 1
        delay_between_requests: 1.0
        max_retries: 3
    
    extraction:
      content_selector: "body"
      remove_selectors:
        - "script"
        - "style"
        - "nav"
        - "footer"
      markdown_options:
        include_images: true
        include_links: true
        preserve_structure: true
        heading_style: "atx"
    
    filters:
      min_content_length: 50
      max_content_length: 500000
      allowed_content_types:
        - "text/html"
      filter_dead_links: true
    
    cleaning:
      profile: "mediawiki"
      config:
        filter_dead_links: true
        remove_citations: true
        remove_categories: true
    
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
      
    strategy:
      type: "recursive"
      max_depth: 3
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
        # ...
      rate_limit:
        requests_per_second: 1
        delay_between_requests: 1.0
        max_retries: 3
    
    extraction:
      content_selector: "body"
      remove_selectors:
        - "script"
        - "style"
        - "nav"
        - "footer"
      markdown_options:
        include_images: true
        include_links: true
        preserve_structure: true
        heading_style: "atx"
    
    filters:
      min_content_length: 50
      max_content_length: 500000
      allowed_content_types:
        - "text/html"
    
    cleaning:
      profile: "mediawiki"
      config:
        filter_dead_links: true
        remove_citations: true
        remove_categories: true
    
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
              mountPath: /app/data/config/sites
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

### Adding New Sites

To add a new site:
1.  Add the YAML configuration to the `webowui-sites` ConfigMap.
2.  Add a new `volumeMount` entry in the Deployment for the new file.
3.  Apply the changes: `kubectl apply -f webowui.yaml`.
4.  Restart the pod to pick up the new mount: `kubectl rollout restart deployment/web-to-openwebui -n web-to-openwebui`.

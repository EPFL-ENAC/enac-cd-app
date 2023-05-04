# ENAC Continuous Deployment Application

To see the mermaid diagrams in VSCode, install [bierner.markdown-mermaid](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid)

## Workflow for an App Continuous Deployment

```mermaid
sequenceDiagram
    participant GHR as Github/Gitlab Runner
    participant CD as enac-prod-cd-app.epfl.ch
    box Redis
    participant R-App as Redis-DeployedApp
    participant R-Running as Redis-RunningAppDeployment
    end
    participant enacit-ansible as enacit-ansible container

    Note over GHR: Phase 1: Request from external Runner

    GHR->>CD: POST /app-deploy/ deployment_id=myapp1 deployment_secret=secret1
    CD->>R-App: does that app exist?
    R-App->>CD: yes, it has inventory="inventory1"
    CD->>R-Running: is that inventory already being deployed?\nif not set its status to "starting"
    R-Running->>CD: ok, status is "starting" and job_id is "jobid-123"
    CD->>enacit-ansible: run app-deploy with inventory="inventory1" and job_id="jobid-123" in a new container
    CD->>GHR: ok, job_id is "jobid-123", status is "starting"

    Note over enacit-ansible: Phase 2: Processing of the app-deploy
    enacit-ansible->>CD: set status for job_id="jobid-123" to "running" with output
    CD->>R-Running: set status for job_id="jobid-123" to "running" with output
    enacit-ansible->>enacit-ansible: do the ansible app deployment

    Note over GHR: Any time the status may be requested
    GHR->>CD: /job-status/ deployment_id=myapp1 deployment_secret=secret1 job_id=jobid-123
    CD->>R-Running: get status for job_id="jobid-123"
    R-Running->>CD: status is "running" with output
    CD->>GHR: status is "running" with output

    Note over enacit-ansible: Phase 3: app-deploy is finished
    enacit-ansible->>CD: set status for job_id="jobid-123" to "finished" with output
    CD->>R-Running: set status for job_id="jobid-123" to "finished" with output

    Note over GHR: Phase 4: Last time the status is requested
    GHR->>CD: /job-status/ deployment_id=myapp1 deployment_secret=secret1 job_id=jobid-123
    CD->>R-Running: get status for job_id="jobid-123"
    R-Running->>CD: status is "finished" with output
    CD->>GHR: status is "finished" with output

```

## Workflow to update Applications list available for CD

```mermaid
sequenceDiagram
    participant GHR as Github/Gitlab Runner
    participant CD as enac-prod-cd-app.epfl.ch
    box Redis
    participant R-App as Redis-DeployedApp
    participant R-Running as Redis-RunningAppDeployment
    end
    participant enacit-ansible as enacit-ansible container
    participant enacit-feed as enacit-ansible feed container

    Note over GHR: Phase 1: Request from external Runner to CD enacit-ansible itself<br/>Everything the same as for App Continuous Deploy

    Note over enacit-ansible: Phase 2: Processing of the app-deploy<br/>Same as for App Continuous Deploy ... but this time it runs on that same server

    enacit-ansible->>enacit-feed: make run
    enacit-feed->>CD: This is the list of all apps available for CD
    CD->>R-App: update the list of all apps available for CD
    R-App->>CD: ok
    CD->>enacit-feed: ok

    Note over enacit-ansible: Phase 3: app-deploy is finished<br/>Same as for App Continuous Deploy

    Note over GHR: Phase 4: Last time the status is requested<br/>Same as for App Continuous Deploy
```

# WIP - Work in progress

## Play the app

```bash
make generate-selfsigned-cert

touch .env
cat << EOF > .secret.env
export REDIS_PASSWORD=secret
EOF

make run
```

Browse RedisInsight at http://localhost:8001

Simulate a app-deploy:

```bash
http --verify no POST "https://localhost/set-available-apps/" < sample_inventory.json
# HTTP/1.1 200 OK
# Content-Length: 15
# Content-Type: application/json
# Date: Tue, 02 May 2023 13:57:55 GMT
# Server: uvicorn

# {
#     "status": "ok"
# }


http --verify no POST https://localhost/app-deploy/ deployment_id=app-one deployment_secret=secret123
# # works 1st time
# HTTP/1.1 200 OK
# Content-Length: 71
# Content-Type: application/json
# Date: Tue, 02 May 2023 13:59:23 GMT
# Server: uvicorn

# {
#     "job_id": "01GZEC5GJHFKWMK4Z5A1NM9DPF",
#     "output": "",
#     "status": "starting"
# }

# # fails other times
# HTTP/1.1 200 OK
# Content-Length: 62
# Content-Type: application/json
# Date: Tue, 02 May 2023 13:59:58 GMT
# Server: uvicorn

# {
#     "error": "App deployment is already running",
#     "status": "error"
# }

http --verify no POST https://localhost/job-status/ deployment_id=app-one deployment_secret=secret123 job_id=01GZEC5GJHFKWMK4Z5A1NM9DPF
# HTTP/1.1 200 OK
# Content-Length: 71
# Content-Type: application/json
# Date: Tue, 02 May 2023 14:00:52 GMT
# Server: uvicorn

# {
#     "job_id": "01GZEC5GJHFKWMK4Z5A1NM9DPF",
#     "output": "",
#     "status": "starting"
# }


http --verify no "https://localhost/get-available-apps/"
# HTTP/1.1 200 OK
# Content-Length: 209
# Content-Type: application/json
# Date: Tue, 02 May 2023 14:01:25 GMT
# Server: uvicorn

# {
#     "inventory": [
#         {
#             "deployment_id": "app-one",
#             "deployment_secret": "secret123",
#             "inventory": "app-one.epfl.ch"
#         },
#         {
#             "deployment_id": "app-two",
#             "deployment_secret": "secretABC",
#             "inventory": "app-two.epfl.ch"
#         }
#     ],
#     "status": "ok"
# }
```

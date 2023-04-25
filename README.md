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

    GHR->>CD: /app-deploy/?name=myapp1&key=secret1
    CD->>R-App: does that app exist?
    R-App->>CD: yes, it has inventory="inventory1"
    CD->>R-Running: is that inventory already being deployed?\nif not set its status to "starting"
    R-Running->>CD: ok, status is "starting" and job_id is "jobid-123"
    CD->>enacit-ansible: run app-deploy with inventory="inventory1" and job_id="jobid-123" in a new container
    CD->>GHR: ok, job_id is "jobid-123", status is "starting"

    Note over enacit-ansible: Phase 2: Processing of the app-deploy
    enacit-ansible->>CD: set status for job_id="jobid-123" to "running"
    CD->>R-Running: set status for job_id="jobid-123" to "running"
    enacit-ansible->>enacit-ansible: do the ansible app deployment

    Note over GHR: Any time the status may be requested
    GHR->>CD: /job-status/?job_id=jobid-123
    CD->>R-Running: get status for job_id="jobid-123"
    R-Running->>CD: status is "running"
    CD->>GHR: status is "running"

    Note over enacit-ansible: Phase 3: app-deploy is done
    enacit-ansible->>CD: set status for job_id="jobid-123" to "done"
    CD->>R-Running: set status for job_id="jobid-123" to "done"

    Note over GHR: Phase 4: Last time the status is requested
    GHR->>CD: /job-status/?job_id=jobid-123
    CD->>R-Running: get status for job_id="jobid-123"
    R-Running->>CD: status is "done"
    CD->>GHR: status is "done"

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

    Note over enacit-ansible: Phase 3: app-deploy is done<br/>Same as for App Continuous Deploy

    Note over GHR: Phase 4: Last time the status is requested<br/>Same as for App Continuous Deploy
```

# WIP - Work in progress

## Play the app

```bash
make generate-selfsigned-cert
make run
```

Browse RedisInsight at http://localhost:8001

Simulate a app-deploy:

```bash
http --verify no "https://localhost/app-deploy/?name=myapp1&key=secret1"
# # works 1st time
# HTTP/1.1 200 OK
# Content-Length: 84
# Content-Type: application/json
# Date: Thu, 13 Apr 2023 08:22:37 GMT
# Server: uvicorn

# {
#     "job_id": "01GXWVB721DKCAZENADFNKNM4G",
#     "status": "starting"
# }

# # fails other times
# HTTP/1.1 200 OK
# Content-Length: 62
# Content-Type: application/json
# Date: Thu, 13 Apr 2023 08:22:47 GMT
# Server: uvicorn

# {
#     "error": "App deployment is already running",
#     "status": "error"
# }

http --verify no "https://localhost/job-status/?name=myapp1&key=secret1&job_id=01GXWVB721DKCAZENADFNKNM4G"
# HTTP/1.1 200 OK
# Content-Length: 75
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 09:37:08 GMT
# Server: uvicorn

# {
#     "job_id": "01GXWVB721DKCAZENADFNKNM4G",
#     "output": "TODO",
#     "status": "starting"
# }

http --verify no POST "https://localhost/set-available-apps/" < sample_inventory.json
# HTTP/1.1 200 OK
# Content-Length: 15
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:16:05 GMT
# Server: uvicorn

# {
#     "status": "ok"
# }

# TODO: removed this debug endpoint
http --verify no "https://localhost/get-available-apps/"
# HTTP/1.1 200 OK
# Content-Length: 177
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:16:23 GMT
# Server: uvicorn

# {
#     "inventory": [
#         {
#             "app_name": "app-one",
#             "inventory": "app-one.epfl.ch",
#             "secret": "secret123"
#         },
#         {
#             "app_name": "app-two",
#             "inventory": "app-two.epfl.ch",
#             "secret": "secretABC"
#         }
#     ],
#     "status": "ok"
# }
```

Testing fake status update: (TODO: remove this fake!)

```bash
http --verify no "https://localhost/job-status/?name=myapp1&key=secret1&job_id=01GYWA8F0GMDM5GGNTVPYSWEYK"

# HTTP/1.1 200 OK
# Content-Length: 75
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:44:34 GMT
# Server: uvicorn

# {
#     "job_id": "01GYWA8F0GMDM5GGNTVPYSWEYK",
#     "output": "TODO",
#     "status": "starting"
# }

http --verify no "https://localhost/job-status/?name=myapp1&key=secret1&job_id=01GYWA8F0GMDM5GGNTVPYSWEYK"

# HTTP/1.1 200 OK
# Content-Length: 74
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:44:35 GMT
# Server: uvicorn

# {
#     "job_id": "01GYWA8F0GMDM5GGNTVPYSWEYK",
#     "output": "TODO",
#     "status": "running"
# }

http --verify no "https://localhost/job-status/?name=myapp1&key=secret1&job_id=01GYWA8F0GMDM5GGNTVPYSWEYK"

# HTTP/1.1 200 OK
# Content-Length: 75
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:44:37 GMT
# Server: uvicorn

# {
#     "job_id": "01GYWA8F0GMDM5GGNTVPYSWEYK",
#     "output": "TODO",
#     "status": "finished"
# }

http --verify no "https://localhost/job-status/?name=myapp1&key=secret1&job_id=01GYWA8F0GMDM5GGNTVPYSWEYK"

# HTTP/1.1 200 OK
# Content-Length: 75
# Content-Type: application/json
# Date: Tue, 25 Apr 2023 13:44:38 GMT
# Server: uvicorn

# {
#     "job_id": "01GYWA8F0GMDM5GGNTVPYSWEYK",
#     "output": "TODO",
#     "status": "finished"
# }
```

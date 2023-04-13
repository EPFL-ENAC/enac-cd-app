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
```

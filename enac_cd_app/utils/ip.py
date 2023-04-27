import ipaddress
import os

import docker
from fastapi import HTTPException, Request

DOCKER_NETWORK = "enac-cd-app_default"


async def check_ip_is_local(request: Request) -> bool:
    """
    Check if the IP is local
    """
    # Get the client's IP address (X-Forwarded-For is set by the reverse proxy)
    client_host = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if client_host == "":  # if X-Forwarded-For is not set then use the client's IP
        client_host = request.client.host
    client_ip = ipaddress.ip_address(client_host)

    # get docker's network network details
    docker_client = docker.from_env()
    container_id = os.environ.get("HOSTNAME")
    container = docker_client.containers.get(container_id)
    container_network = container.attrs["NetworkSettings"]["Networks"][DOCKER_NETWORK]
    ip_network = ipaddress.IPv4Network(
        f"{container_network['IPAddress']}/{container_network['IPPrefixLen']}",
        strict=False,
    )

    # raise 403 Forbidden if the client's IP is not in the same network
    if not ip_network.overlaps(ipaddress.IPv4Network(f"{client_ip}/32")):
        raise HTTPException(status_code=403, detail="Access denied")

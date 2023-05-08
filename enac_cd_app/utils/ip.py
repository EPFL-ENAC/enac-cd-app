import ipaddress
import os

import docker
from fastapi import HTTPException, Request

DOCKER_NETWORK = "enac-cd-app_default"
MONITORING_IP = os.environ.get("MONITORING_IP")


def get_client_ip(request: Request) -> ipaddress.IPv4Address:
    # Get the client's IP address (X-Forwarded-For is set by the reverse proxy)
    client_host = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if client_host == "":  # if X-Forwarded-For is not set then use the client's IP
        client_host = request.client.host
    client_ip = ipaddress.ip_address(client_host)
    return client_ip


def is_ip_local(client_ip: ipaddress.IPv4Address) -> bool:
    # get docker's network network details
    docker_client = docker.from_env()
    container_id = os.environ.get("HOSTNAME")
    container = docker_client.containers.get(container_id)
    container_network = container.attrs["NetworkSettings"]["Networks"][DOCKER_NETWORK]
    ip_network = ipaddress.IPv4Network(
        f"{container_network['IPAddress']}/{container_network['IPPrefixLen']}",
        strict=False,
    )

    return ip_network.overlaps(ipaddress.IPv4Network(f"{client_ip}/32"))


async def check_ip_is_local(request: Request) -> bool:
    """
    Check if the IP is local
    """
    client_ip = get_client_ip(request)

    # raise 403 Forbidden if the client's IP is not in the same network
    if not is_ip_local(client_ip):
        raise HTTPException(status_code=403, detail="Access denied")


async def check_ip_for_monitoring(request: Request) -> bool:
    client_ip = get_client_ip(request)

    if not (client_ip == ipaddress.ip_address(MONITORING_IP) or is_ip_local(client_ip)):
        raise HTTPException(status_code=403, detail="Access denied")

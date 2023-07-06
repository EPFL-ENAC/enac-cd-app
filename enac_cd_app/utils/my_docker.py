import logging
import os
import time
import traceback

import docker
from fastapi import BackgroundTasks

from enac_cd_app.utils import my_redis

CD_ENV = os.environ.get("CD_ENV")
GH_USERNAME = os.environ.get("GH_USERNAME")
GH_PAT = os.environ.get("GH_PAT")
SELF_CONTAINER_CHECK_INTERVAL = 5  # seconds
ENAC_CD_APP_ROOT = os.environ.get("ENAC_CD_APP_ROOT")

logger_access = logging.getLogger("uvicorn.access")
logger_error = logging.getLogger("uvicorn.error")


def inject_apps(job_id: str = None) -> None:
    """
    Run enacit-ansible announce-apps in a docker container
    """
    try:
        if job_id is not None:
            my_redis.set_job_status(job_id=job_id, status="running", output="")
        client = docker.from_env()
        client.login(username=GH_USERNAME, password=GH_PAT, registry="ghcr.io")
        client.images.pull("ghcr.io/epfl-enac/enacit-ansible", tag="latest")
        output = client.containers.run(
            "ghcr.io/epfl-enac/enacit-ansible:latest",
            "announce-apps",
            volumes={
                f"{ENAC_CD_APP_ROOT}/.ssh": {"bind": "/opt/root/.ssh", "mode": "ro"},
                f"{ENAC_CD_APP_ROOT}/.enacit-ansible_vault_password": {
                    "bind": "/root/.enacit-ansible_vault_password",
                    "mode": "rw",
                },
                "/etc/localtime": {
                    "bind": "/etc/localtime",
                    "mode": "ro",
                },
            },
            environment={
                "CD_ENV": CD_ENV,
            },
            network="enac-cd-app_default",
        )
        output = output.decode("utf-8")
        print(output, flush=True)
        if job_id is not None:
            my_redis.set_job_status(job_id=job_id, status="success", output=output)
    except Exception as e:
        logger_error.error(f"Error while running enacit-ansible announce-apps: {e}")
        logger_error.error(traceback.format_exc())
        if job_id is not None:
            my_redis.set_job_status(job_id=job_id, status="error", output=str(e))


def app_deploy(
    deployment_id: str, inventory: str, job_id: str, background_tasks: BackgroundTasks
) -> None:
    """
    Run enacit-ansible app-deploy in a docker container
    """
    try:
        client = docker.from_env()
        client.login(username=GH_USERNAME, password=GH_PAT, registry="ghcr.io")
        client.images.pull("ghcr.io/epfl-enac/enacit-ansible", tag="latest")
        container = client.containers.run(
            "ghcr.io/epfl-enac/enacit-ansible:latest",
            f"app-deploy {inventory} {job_id}",
            volumes={
                f"{ENAC_CD_APP_ROOT}/.ssh": {
                    "bind": "/opt/root/.ssh",
                    "mode": "ro",
                },
                f"{ENAC_CD_APP_ROOT}/.enacit-ansible_vault_password": {
                    "bind": "/root/.enacit-ansible_vault_password",
                    "mode": "rw",
                },
                "/etc/localtime": {
                    "bind": "/etc/localtime",
                    "mode": "ro",
                },
            },
            environment={
                "CD_ENV": CD_ENV,
            },
            network="enac-cd-app_default",
            detach=True,
            pid_mode="host",
        )
        my_redis.set_container_id(container_id=container.id, job_id=job_id)
        logger_access.info(
            f"{job_id=} Launched app-deploy of {deployment_id} "
            f"in container {container.short_id}"
        )
        check_container(
            container_id=container.id,
            job_id=job_id,
            periodic_check=True,
            background_tasks=background_tasks,
        )
    except Exception as e:
        logger_error.error(f"Error while running enacit-ansible app-deploy: {e}")
        logger_error.error(traceback.format_exc())
        my_redis.set_job_status(job_id=job_id, status="error", output=str(e))


def check_container(
    container_id: str,
    job_id: str,
    periodic_check: bool = False,
    background_tasks: BackgroundTasks = None,
) -> None:
    """
    Check if container is still running
    get output and status from it
    """
    try:
        container = docker.from_env().containers.get(container_id)
        # read container logs
        output = container.logs().decode("utf-8")
        if container.status == "running":
            # if container is still running, update output and status
            my_redis.set_job_status(job_id=job_id, status="running", output=output)
            if periodic_check:
                time.sleep(SELF_CONTAINER_CHECK_INTERVAL)
                background_tasks.add_task(
                    check_container,
                    container_id,
                    job_id,
                    periodic_check,
                    background_tasks,
                )
        else:
            if output.endswith("Process terminated with return code: 0\n"):
                my_redis.set_job_status(job_id=job_id, status="success", output=output)
            else:
                my_redis.set_job_status(job_id=job_id, status="error", output=output)
    except Exception as e:
        logger_error.error(f"Error while checking enacit-ansible container: {e}")
        logger_error.error(traceback.format_exc())
        my_redis.set_job_status(job_id=job_id, status="error", output=str(e))

import os
import time

import docker
from fastapi import BackgroundTasks

from enac_cd_app.utils import my_redis, my_redis_models

CD_ENV = os.environ.get("CD_ENV")
GH_USERNAME = os.environ.get("GH_USERNAME")
GH_PAT = os.environ.get("GH_PAT")


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
                "/opt/enac-cd-app/root/.ssh": {"bind": "/opt/root/.ssh", "mode": "ro"},
                "/opt/enac-cd-app/root/.enacit-ansible_vault_password": {
                    "bind": "/root/.enacit-ansible_vault_password",
                    "mode": "rw",
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
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )
        if job_id is not None:
            my_redis.set_job_status(job_id=job_id, status="error", output=str(e))


def app_deploy(inventory: str, job_id: str, background_tasks: BackgroundTasks) -> None:
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
                "/opt/enac-cd-app/root/.ssh": {
                    "bind": "/opt/root/.ssh",
                    "mode": "ro",
                },
                "/opt/enac-cd-app/root/.enacit-ansible_vault_password": {
                    "bind": "/root/.enacit-ansible_vault_password",
                    "mode": "rw",
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
        print(f"Launched app-deploy in container {container}", flush=True)
        check_container(
            my_redis.get_running_app_deployment(inventory=inventory, job_id=job_id),
            periodic_check=True,
            background_tasks=background_tasks,
        )
    except Exception as e:
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )


def check_container(
    deployment: my_redis_models.RunningAppDeployment,
    periodic_check: bool = False,
    background_tasks: BackgroundTasks = None,
) -> None:
    """
    Check if container is still running
    get output and status from it
    """
    container = docker.from_env().containers.get(deployment.container_id)
    # read container logs
    output = container.logs().decode("utf-8")
    if container.status == "running":
        # if container is still running, update output and status
        my_redis.set_job_status(job_id=deployment.pk, status="running", output=output)
        if periodic_check:
            time.sleep(2)
            background_tasks.add_task(
                check_container, deployment, periodic_check, background_tasks
            )
    else:
        if output.endswith("Process terminated with return code: 0\n"):
            my_redis.set_job_status(
                job_id=deployment.pk, status="success", output=output
            )
        else:
            my_redis.set_job_status(job_id=deployment.pk, status="error", output=output)
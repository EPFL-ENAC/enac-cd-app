import os
import time
from multiprocessing import Process
from typing import Dict, List

import docker
from fastapi import BackgroundTasks, Depends, FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils import redis
from enac_cd_app.utils.ip import check_ip_is_local

CD_ENV = os.environ.get("CD_ENV")
GH_USERNAME = os.environ.get("GH_USERNAME")
GH_PAT = os.environ.get("GH_PAT")

app = FastAPI(
    title=__name__,
    version=__version__,
)


def inject_apps():
    """
    Run enacit-ansible announce-apps in a docker container
    """
    try:
        client = docker.from_env()
        client.login(username=GH_USERNAME, password=GH_PAT, registry="ghcr.io")
        output = client.containers.run(
            "ghcr.io/epfl-enac/enacit-ansible:latest",
            "announce-apps",
            volumes={
                "/opt/enac-cd-app/root/.ssh": {"bind": "/opt/root/.ssh", "mode": "ro"},
                "/opt/enac-cd-app/root/.enacit-ansible_vault_password": {
                    "bind": "/opt/root/.enacit-ansible_vault_password",
                    "mode": "rw",
                },
            },
            environment={
                "CD_ENV": CD_ENV,
            },
            network="enac-cd-app_default",
        )
        output.decode()
        print(output, flush=True)
    except Exception as e:
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )


@app.get("/")
async def get_root():
    """
    Root endpoint
    """
    return {"app": __name__, "version": __version__}


def app_deploy(inventory: str, job_id: str):
    try:
        client = docker.from_env()
        client.login(username=GH_USERNAME, password=GH_PAT, registry="ghcr.io")
        output = client.containers.run(
            "ghcr.io/epfl-enac/enacit-ansible:latest",
            f"app-deploy {inventory} {job_id}",
            volumes={
                "/opt/enac-cd-app/root/.ssh": {
                    "bind": "/opt/root/.ssh",
                    "mode": "ro",
                },
                "/opt/enac-cd-app/root/.enacit-ansible_vault_password": {
                    "bind": "/opt/root/.enacit-ansible_vault_password",
                    "mode": "rw",
                },
            },
            environment={
                "CD_ENV": CD_ENV,
            },
            network="enac-cd-app_default",
        )
        output.decode()
        print(output, flush=True)
    except Exception as e:
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )


@app.get("/app-deploy/")
async def get_app_deploy(name: str, key: str, background_tasks: BackgroundTasks):
    """
    Deploy an app
    name and key must match an inventory from the database
    """
    try:
        inventory = redis.get_app_inventory(app_name=name, secret_key=key)
        job_id = redis.set_deploy_starting(inventory=inventory)
        background_tasks.add_task(app_deploy, inventory, job_id)

        return {
            "status": "starting",
            "job_id": job_id,
            "output": "",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/set-job-status/", dependencies=[Depends(check_ip_is_local)])
async def set_job_status(payload: dict):
    job_id = payload.get("job_id")
    status = payload.get("status")
    output = payload.get("output")
    redis.set_job_status(job_id=job_id, status=status, output=output)
    return {"status": "saved"}


@app.get("/job-status/")
async def get_job_status(name: str, key: str, job_id: str):
    """
    Get the status of a job
    name and key must match an inventory from the database
    """
    try:
        inventory = redis.get_app_inventory(app_name=name, secret_key=key)
        running_job = redis.read_job_status(inventory=inventory, job_id=job_id)
        return {
            "status": running_job.get("status"),
            "job_id": job_id,
            "output": running_job.get("output"),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/set-available-apps/", dependencies=[Depends(check_ip_is_local)])
async def post_set_available_apps(inventory: List[Dict]):
    """
    Set the available apps from inventory to the database
    """
    try:
        redis.set_available_apps(inventory=inventory)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/get-available-apps/", dependencies=[Depends(check_ip_is_local)])
async def get_get_available_apps():
    """
    Get the available apps from the database
    """
    try:
        return {"status": "ok", "inventory": redis.get_available_apps()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/inject-apps/", dependencies=[Depends(check_ip_is_local)])
async def get_inject_apps(background_tasks: BackgroundTasks):
    """
    TODO remove this endpoint
    """
    background_tasks.add_task(inject_apps)

    return {"status": "launched"}


def init():
    time.sleep(2)  # be sure FastAPI is ready
    inject_apps()


@app.on_event("startup")
async def startup_event():
    """
    On startup, inject apps in an other process
    """
    p = Process(target=init)
    p.start()

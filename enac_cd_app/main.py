import datetime
import os
import time
from multiprocessing import Process
from typing import Dict, List

import docker
from fastapi import BackgroundTasks, Depends, FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils import redis, redis_models
from enac_cd_app.utils.ip import check_ip_for_monitoring, check_ip_is_local

CD_ENV = os.environ.get("CD_ENV")
GH_USERNAME = os.environ.get("GH_USERNAME")
GH_PAT = os.environ.get("GH_PAT")

app = FastAPI(
    title=__name__,
    version=__version__,
)


def inject_apps(job_id: str = None):
    """
    Run enacit-ansible announce-apps in a docker container
    """
    try:
        if job_id is not None:
            redis.set_job_status(job_id=job_id, status="running", output="")
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
            redis.set_job_status(job_id=job_id, status="success", output=output)
    except Exception as e:
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )
        if job_id is not None:
            redis.set_job_status(job_id=job_id, status="error", output=str(e))


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
        print(f"Launched app-deploy in container {container}", flush=True)
    except Exception as e:
        print(
            f"Error while running enacit-ansible announce-apps: {str(e)}",
            flush=True,
        )


@app.post("/app-deploy/")
async def get_app_deploy(payload: dict, background_tasks: BackgroundTasks):
    """
    Deploy an app
    deployment_id and deployment_secret must match an inventory from the database
    """
    try:
        deployment_id = payload.get("deployment_id")
        deployment_secret = payload.get("deployment_secret")
        inventory = redis.get_app_inventory(
            deployment_id=deployment_id, deployment_secret=deployment_secret
        )
        deployment = redis.set_deploy_starting(inventory=inventory)
        if deployment["need_to_start"]:
            if inventory == "cd_runner_with_enacit_ansible":
                # Special case to CD enacit-ansible on self
                background_tasks.add_task(
                    inject_apps, deployment["running_app_deployment"].pk
                )
            else:
                background_tasks.add_task(
                    app_deploy, inventory, deployment["running_app_deployment"].pk
                )

        return {
            "status": redis_models.RunningStates(
                deployment["running_app_deployment"].status
            ).name.lower(),
            "job_id": deployment["running_app_deployment"].pk,
            "output": deployment["running_app_deployment"].output,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/set-job-status/", dependencies=[Depends(check_ip_is_local)])
async def set_job_status(payload: dict):
    job_id = payload.get("job_id")
    status = payload.get("status")
    output = payload.get("output")

    # add datetime at every beginning of line
    output = "\n".join(
        [
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {line}"
            for line in output.rstrip().split("\n")
        ]
    )
    output = f"{output}\n"

    redis.set_job_status(job_id=job_id, status=status, output=output)
    return {"status": "saved"}


@app.post("/job-status/")
async def get_job_status(payload: dict):
    """
    Read the status of a job
    deployment_id and deployment_secret must match an inventory from the database
    """
    try:
        deployment_id = payload.get("deployment_id")
        deployment_secret = payload.get("deployment_secret")
        job_id = payload.get("job_id")
        inventory = redis.get_app_inventory(
            deployment_id=deployment_id, deployment_secret=deployment_secret
        )
        deployment = redis.get_running_app_deployment(
            inventory=inventory, job_id=job_id
        )
        return {
            "status": redis_models.RunningStates(deployment.status).name.lower(),
            "job_id": job_id,
            "output": deployment.output,
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


@app.get("/load/", dependencies=[Depends(check_ip_for_monitoring)])
async def get_load():
    """
    Return Redis activity load
    """
    try:
        load_report = redis.get_load_report()
        return {"status": "ok", "load": load_report}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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

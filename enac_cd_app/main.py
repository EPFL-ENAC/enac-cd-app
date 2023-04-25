from typing import List

import docker
from fastapi import Depends, FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils import redis
from enac_cd_app.utils.ip import check_ip_is_local

app = FastAPI(
    title=__name__,
    version=__version__,
)

# TODO: remove this
redis.inject_apps()
redis.remove_all_running_app_deployments()


@app.get("/")
def get_root():
    """
    Root endpoint
    """
    return {"app": __name__, "version": __version__}


@app.get("/app-deploy/")
def get_app_deploy(name: str, key: str):
    """
    Deploy an app
    name and key must match an inventory from the database
    """
    try:
        inventory = redis.get_app_inventory(app_name=name, secret_key=key)
        job_id = redis.set_deploy_starting(inventory=inventory)
        try:
            client = docker.from_env()
            # enacit-ansible app-deploy --inventory inventory_123
            output = client.containers.run("ubuntu", "echo hello world")
            output.decode()
        except Exception as e:
            output = f"docker error: {str(e)}"

        return {
            "status": "starting",
            "job_id": job_id,
            "output": output,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/job-status/")
def get_job_status(name: str, key: str, job_id: str):
    """
    Get the status of a job
    name and key must match an inventory from the database
    """
    try:
        inventory = redis.get_app_inventory(app_name=name, secret_key=key)
        job_status = redis.get_job_status(inventory=inventory, job_id=job_id)
        return {
            "status": job_status,
            "job_id": job_id,
            "output": "TODO",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/set-available-apps/", dependencies=[Depends(check_ip_is_local)])
def post_set_available_apps(inventory: List):
    """
    Set the available apps from inventory to the database
    """
    try:
        redis.set_available_apps(inventory=inventory)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/get-available-apps/", dependencies=[Depends(check_ip_is_local)])
def get_get_available_apps():
    """
    Get the available apps from the database
    """
    try:
        return {"status": "ok", "inventory": redis.get_available_apps()}
    except Exception as e:
        return {"status": "error", "error": str(e)}

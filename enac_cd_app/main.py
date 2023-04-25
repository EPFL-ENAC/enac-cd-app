import docker
from fastapi import Depends, FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils.ip import check_ip_is_local
from enac_cd_app.utils.redis import (
    get_app_inventory,
    get_job_status,
    inject_apps,
    remove_all_running_app_deployments,
    set_deploy_starting,
)

app = FastAPI(
    title=__name__,
    version=__version__,
)

# TODO: remove this
inject_apps()
remove_all_running_app_deployments()


@app.get("/")
def read_root():
    """
    Root endpoint
    """
    return {"app": __name__, "version": __version__}


@app.get("/app-deploy/")
def app_deploy(name: str, key: str):
    """
    Deploy an app
    name and key must match an inventory from the database
    """
    try:
        inventory = get_app_inventory(app_name=name, secret_key=key)
        job_id = set_deploy_starting(inventory=inventory)
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
def job_status(name: str, key: str, job_id: str):
    """
    Get the status of a job
    name and key must match an inventory from the database
    """
    try:
        inventory = get_app_inventory(app_name=name, secret_key=key)
        job_status = get_job_status(inventory=inventory, job_id=job_id)
        return {
            "status": job_status,
            "job_id": job_id,
            "output": "TODO",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/protected/", dependencies=[Depends(check_ip_is_local)])
def protected():
    return {"answer": "Allowed, your IP is local"}

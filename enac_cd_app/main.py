import time
from multiprocessing import Process
from typing import Dict, List

from fastapi import BackgroundTasks, Depends, FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils import my_docker, redis, redis_models
from enac_cd_app.utils.ip import check_ip_for_monitoring, check_ip_is_local

app = FastAPI(
    title=__name__,
    version=__version__,
)


@app.get("/")
async def get_root():
    """
    Root endpoint
    """
    return {"app": __name__, "version": __version__}


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
                    my_docker.inject_apps, deployment["running_app_deployment"].pk
                )
            else:
                background_tasks.add_task(
                    my_docker.app_deploy,
                    inventory,
                    deployment["running_app_deployment"].pk,
                    background_tasks,
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
        if deployment.status in (
            redis_models.RunningStates.STARTING,
            redis_models.RunningStates.RUNNING,
        ):
            my_docker.check_container(deployment)
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
    TODO remove this endpoint
    Get the available apps from the database
    """
    print("!!!!!!!!!!!!!!!!!!!!! TODO remove this endpoint", flush=True)
    try:
        return {"status": "ok", "inventory": redis.get_available_apps()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/inject-apps/", dependencies=[Depends(check_ip_is_local)])
async def get_inject_apps(background_tasks: BackgroundTasks):
    """
    TODO remove this endpoint
    """
    print("!!!!!!!!!!!!!!!!!!!!! TODO remove this endpoint", flush=True)
    background_tasks.add_task(my_docker.inject_apps)

    return {"status": "launched"}


@app.get("/load/", dependencies=[Depends(check_ip_for_monitoring)])
async def get_load(periods: str = "1_hour:3600,1_day:86400,1_week:604800"):
    """
    Return Redis activity load for the time periods requested
    periods="1_hour:3600,1_day:86400,1_week:604800"
    """
    try:
        query: dict[str, int] = {
            period_name: int(period_seconds)
            for period_name, period_seconds in [
                period.split(":") for period in periods.split(",")
            ]
        }
        load_report = redis.get_load_report(query)
        return {"status": "ok", "load": load_report}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def init():
    time.sleep(2)  # be sure FastAPI is ready
    my_docker.inject_apps()


@app.on_event("startup")
async def startup_event():
    """
    On startup, inject apps in an other process
    """
    p = Process(target=init)
    p.start()

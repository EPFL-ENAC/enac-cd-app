"""
This is to define all interactions with redis
"""

import datetime
import logging
from typing import List

from redis_om import Migrator
from redis_om.model.model import NotFoundError

from .my_redis_models import DeployedApp, RunningAppDeployment, RunningStates

REDIS_TMP_ENTRIES_TTL = 60 * 60 * 24 * 7  # 7 day
logger_access = logging.getLogger("uvicorn.access")


def set_available_apps(inventory: List):
    """
    Example of inventory:
    inventory = [
        {
            "inventory": "app-one.epfl.ch",
            "deployment_id": "app-one",
            "deployment_secret": "secret123",
        },
        {
            "inventory": "app-two.epfl.ch",
            "deployment_id": "app-two",
            "deployment_secret": "secretABC",
        }
    ]
    """
    # remove all existing apps
    for pk in DeployedApp.all_pks():
        DeployedApp.delete(pk=pk)

    # add new apps
    for app in inventory:
        DeployedApp(
            inventory=app["inventory"],
            deployment_id=app["deployment_id"],
            deployment_secret=app["deployment_secret"],
        ).save()


def get_app_inventory(deployment_id: str, deployment_secret: str) -> str:
    """
    Get the inventory of an app
    """
    try:
        app = DeployedApp.find(DeployedApp.deployment_id == deployment_id).first()
    except NotFoundError:
        raise Exception("App not found")
    if app.deployment_secret != deployment_secret:
        # we don't want to leak the existence of the app
        raise Exception("App not found")
    return app.inventory


def set_deploy_starting(inventory: str) -> int:
    """
    Save the status of an app deployment to starting
    """
    # Check if the app deployment is already running
    need_to_start = True
    running_app_deployment = None
    try:
        for running_deploy in RunningAppDeployment.find(
            RunningAppDeployment.inventory == inventory
        ).all():
            if running_deploy.status in (
                RunningStates.STARTING,
                RunningStates.RUNNING,
            ):
                need_to_start = False
                running_app_deployment = running_deploy
    except NotFoundError:
        pass

    if running_app_deployment is None:
        running_app_deployment = RunningAppDeployment(
            inventory=inventory,
            status=RunningStates.STARTING,
            started_at=datetime.datetime.now(),
            output="",
            container_id="",
        )
        running_app_deployment.expire(REDIS_TMP_ENTRIES_TTL)
        running_app_deployment.save()

    return {
        "running_app_deployment": running_app_deployment,
        "need_to_start": need_to_start,
    }


def get_running_app_deployment(inventory: str, job_id: str) -> RunningAppDeployment:
    """
    Return RunningAppDeployment matching inventory and job_id
    """
    try:
        deployment = RunningAppDeployment.find(
            RunningAppDeployment.inventory == inventory
            and RunningAppDeployment.pk == job_id
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")

    return deployment


def set_container_id(job_id: str, container_id=str) -> None:
    """
    Set the container_id of a job
    """
    try:
        running_deploy = RunningAppDeployment.find(
            RunningAppDeployment.pk == job_id
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")
    running_deploy.container_id = container_id
    running_deploy.save()


def set_job_status(job_id: str, output: str, status: str) -> None:
    """
    Set the status of a job
    """
    try:
        running_deploy = RunningAppDeployment.find(
            RunningAppDeployment.pk == job_id
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")
    if running_deploy.status != RunningStates[status.upper()]:
        logger_access.info(f"{job_id=} Changed to {status=}")
    running_deploy.output = output
    running_deploy.status = RunningStates[status.upper()]
    running_deploy.expire(REDIS_TMP_ENTRIES_TTL)
    running_deploy.save()


def get_load_report(query: dict[str, int]) -> dict:
    """
    Return a dict with the health of the app
    for requested periods
        query = {'1_hour': 3600, '1_day': 86400, '1_week': 604800}
        nb of jobs with starting, running, success, error
    """
    now = datetime.datetime.now()
    periods = {
        name: now - datetime.timedelta(seconds=seconds)
        for name, seconds in query.items()
    }
    load_report = {
        period: {status: 0 for status in ["starting", "running", "success", "error"]}
        for period in periods
    }
    for running_deploy in RunningAppDeployment.find().all():
        for period in periods:
            if running_deploy.started_at > periods[period]:
                load_report[period][
                    RunningStates(running_deploy.status).name.lower()
                ] += 1

    return load_report


# Before running queries, we need to run migrations to set up the
# indexes that Redis OM will use. You can also use the `migrate`
# CLI tool for this!
Migrator().run()

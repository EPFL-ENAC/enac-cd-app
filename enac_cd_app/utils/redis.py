"""
This is to define all interactions with redis
"""

import datetime
from typing import List

from redis_om import Migrator
from redis_om.model.model import NotFoundError

from .redis_models import DeployedApp, RunningAppDeployment, RunningStates


def get_available_apps() -> List:
    # TODO: remove this
    inventory = []
    for pk in DeployedApp.all_pks():
        app = DeployedApp.find(DeployedApp.pk == pk).first()
        inventory.append(
            {
                "inventory": app.inventory,
                "deployment_id": app.deployment_id,
                "deployment_secret": app.deployment_secret,
            }
        )
    return inventory


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
    try:
        for running_deploy in RunningAppDeployment.find(
            RunningAppDeployment.inventory == inventory
        ).all():
            if running_deploy.status in (
                RunningStates.STARTING,
                RunningStates.RUNNING,
            ):
                raise Exception("App deployment is already running")
    except NotFoundError:
        pass

    starting_deploy = RunningAppDeployment(
        inventory=inventory,
        status=RunningStates.STARTING,
        started_at=datetime.datetime.now(),
        output="",
    ).save()
    return starting_deploy.pk


def read_job_status(inventory: str, job_id: str) -> str:
    """
    Get the status of a job
    """
    try:
        running_deploy = RunningAppDeployment.find(
            RunningAppDeployment.inventory == inventory
            and RunningAppDeployment.pk == job_id
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")
    output = running_deploy.output
    running_deploy.output = ""  # clear the output
    running_deploy.save()
    return {
        "status": RunningStates(running_deploy.status).name.lower(),
        "output": output,
    }


def set_job_status(job_id: str, status: str, output: str):
    """
    Set the status of a job
    """
    try:
        running_deploy = RunningAppDeployment.find(
            RunningAppDeployment.pk == job_id
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")
    if running_deploy.pk != job_id:
        raise Exception("App deployment not found")
    running_deploy.status = RunningStates[status.upper()]
    running_deploy.output += output
    running_deploy.save()


# Before running queries, we need to run migrations to set up the
# indexes that Redis OM will use. You can also use the `migrate`
# CLI tool for this!
Migrator().run()

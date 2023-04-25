"""
This is to define all interactions with redis
"""

import datetime
from typing import List

from redis_om import Migrator
from redis_om.model.model import NotFoundError

from .redis_models import DeployedApp, RunningAppDeployment, RunningStates


def inject_apps():
    # TODO: remove this
    for app in (
        DeployedApp(
            app_name="myapp1",
            secret_key="secret1",
            inventory="inventory_123",
        ),
        DeployedApp(
            app_name="myapp2",
            secret_key="secret2",
            inventory="inventory_abc",
        ),
    ):
        app.save()


def remove_all_running_app_deployments():
    # TODO: remove this
    for pk in RunningAppDeployment.all_pks():
        RunningAppDeployment.delete(pk=pk)


def get_available_apps() -> List:
    # TODO: remove this
    inventory = []
    for pk in DeployedApp.all_pks():
        app = DeployedApp.find(DeployedApp.pk == pk).first()
        inventory.append(
            {
                "app_name": app.app_name,
                "inventory": app.inventory,
                "secret": app.secret_key,
            }
        )
    return inventory


def set_available_apps(inventory: List):
    """
    Example of inventory:
    inventory = [
        {
        "app_name": "app-one",
        "inventory": "app-one.epfl.ch",
        "secret": "secret123",
        },
        {
        "app_name": "app-two",
        "inventory": "app-two.epfl.ch",
        "secret": "secretABC",
        }
    ]
    """
    # remove all existing apps
    for pk in DeployedApp.all_pks():
        DeployedApp.delete(pk=pk)

    # add new apps
    for app in inventory:
        DeployedApp(
            app_name=app["app_name"],
            secret_key=app["secret"],
            inventory=app["inventory"],
        ).save()


def get_app_inventory(app_name: str, secret_key: str) -> str:
    """
    Get the inventory of an app
    """
    try:
        app = DeployedApp.find(DeployedApp.app_name == app_name).first()
    except NotFoundError:
        raise Exception("App not found")
    if app.secret_key != secret_key:
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
    ).save()
    return starting_deploy.pk


def get_job_status(inventory: str, job_id: int) -> str:
    """
    Get the status of a job
    """
    try:
        running_deploy = RunningAppDeployment.find(
            RunningAppDeployment.inventory == inventory
        ).first()
    except NotFoundError:
        raise Exception("App deployment not found")
    if running_deploy.pk != job_id:
        raise Exception("App deployment not found")
    return RunningStates(running_deploy.status).name.lower()


# Before running queries, we need to run migrations to set up the
# indexes that Redis OM will use. You can also use the `migrate`
# CLI tool for this!
Migrator().run()

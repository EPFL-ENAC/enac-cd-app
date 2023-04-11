"""
This is to define all interactions with redis
"""

import datetime

from redis_om import Migrator
from redis_om.model.model import NotFoundError

from enac_cd_app.utils.redis_models import (
    DeployedApp,
    RunningAppDeployment,
    RunningStates,
)


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


# Before running queries, we need to run migrations to set up the
# indexes that Redis OM will use. You can also use the `migrate`
# CLI tool for this!
Migrator().run()

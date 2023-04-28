import datetime
from enum import IntEnum

from redis_om import Field, JsonModel


class DeployedApp(JsonModel):
    """
    Define an app that can be deployed
    """

    app_name: str = Field(index=True)
    secret_key: str
    inventory: str

    class Meta:
        global_key_prefix = "deployed-app-json"


class RunningStates(IntEnum):
    STARTING = 1
    RUNNING = 2
    FINISHED = 3


class RunningAppDeployment(JsonModel):
    """
    Define a running app deployment
    """

    inventory: str = Field(index=True)
    status: RunningStates
    started_at: datetime.datetime
    output: str

import datetime
from enum import IntEnum

from redis_om import Field, JsonModel


class DeployedApp(JsonModel):
    """
    Define an app that can be deployed
    """

    inventory: str
    deployment_id: str = Field(index=True)
    deployment_secret: str

    class Meta:
        global_key_prefix = "deployed-app-json"


class RunningStates(IntEnum):
    STARTING = 1
    RUNNING = 2
    FINISHED = 3


class RunningAppSuccess(IntEnum):
    STILL_RUNNING = 0
    SUCCESS = 1
    FAILURE = 2


class RunningAppDeployment(JsonModel):
    """
    Define a running app deployment
    """

    inventory: str = Field(index=True)
    status: RunningStates = Field(index=True)
    started_at: datetime.datetime
    output: str
    success: RunningAppSuccess

import datetime
from enum import IntEnum

from redis_om import Field, JsonModel


class DeployedApp(JsonModel, index=True):
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
    SUCCESS = 3
    ERROR = 4


class RunningAppDeployment(JsonModel, index=True):
    """
    Define a running app deployment
    """

    inventory: str = Field(index=True)
    status: RunningStates = Field(index=True)
    started_at: datetime.datetime
    container_id: str
    output: str

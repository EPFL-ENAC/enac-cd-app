import time

from enac_cd_app.utils import my_docker


def init():
    time.sleep(1)  # be sure FastAPI is ready
    my_docker.inject_apps()

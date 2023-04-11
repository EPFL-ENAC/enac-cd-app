from fastapi import FastAPI

from enac_cd_app import __name__, __version__
from enac_cd_app.utils.redis import (
    get_app_inventory,
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
    return {"app": __name__, "version": __version__}


@app.get("/app-deploy/")
def app_deploy(name: str, key: str):
    try:
        inventory = get_app_inventory(app_name=name, secret_key=key)
        job_id = set_deploy_starting(inventory=inventory)
        return {"status": "starting", "job_id": job_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

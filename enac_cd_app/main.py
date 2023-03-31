from fastapi import FastAPI

from enac_cd_app import __name__, __version__

app = FastAPI(
    title=__name__,
    version=__version__,
)


@app.get("/")
def read_root():
    return {"app": __name__, "version": __version__}


@app.get("/app-deploy/")
def read_item(repo: str, key: str):
    return {"repo": repo, "key": key}

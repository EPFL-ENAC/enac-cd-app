UID := $(shell id -u)
GID := $(shell id -g)

dev:
	poetry run uvicorn enac_cd_app.main:app --reload

run:
	docker compose build --pull
	docker compose up -d --remove-orphans

generate-selfsigned-cert:
	cd cert && OWNER="${UID}.${GID}" docker-compose up --remove-orphans

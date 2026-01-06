
# Manual installation


# Docker installation

To run this app in a Docker container, whilst in the app's root directory run:

```bash
docker compose up -d --build
```

- This command starts the service defined in the app's `docker-compose.yml`. `-d` runs the containers in detached mode (in the background instead of using the current terminal) `--build` builds the Docker image before starting the containers - this is useful if you have made changes to the source code or Dockerfile since your last build, or you do not have a previously built image available to use.

- The `docker-compose.yml` is configured to map your local port 5000 to the container's port 5000, and attempts to mount two volumes `data/` and `logs/` to the container from your local current working directory. If either directory is missing, Docker will create the missing directories for you so that they can be mounted.


If you wish to access the container environment through a terminal window you can use:

```bash
docker exec -it parkvar_prod /bin/sh
```

To stop and remove the container after running:

```bash
docker compose down
```
- This uses the container information defined in the `docker-compose.yml` to stop and remove the active container


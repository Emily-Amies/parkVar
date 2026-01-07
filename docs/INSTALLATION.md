
# Installation Guide

parkVar can be installed and run manually in a local Python environment, or launched via a Docker container. This document will cover the process for launching the app using both methods.

## Local Installation

### Requirements

- Python 3.13 (or compatible distribution)
- pip
- Conda or Miniconda for creating environment and gathering based on requirements (recommended) or local venv
- Git

### Clone Latest Repository 

To clone the latest repository 

    git clone https://github.com/Emily-Amies/parkVar.git parkvar-1
    cd parkVar-1

### Create Local Environment

#### Recommended: Create conda environment

Create environment from YAML file, and activate that environment. from project repository root, run the following:

    conda env create -f environment.yml
    conda activate parkvar_env

#### Alternative: Create venv using pip

Create fresh venv and install dependencies from requirements.txt using pip

    python -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

### Install parkVar
To install the app on the local environment, from the project repository root:

	pip install . 

### Alternative: Developer installation
To install editable (for developer purposes and to check test coverage etc.), from project repository root:

    pip install -e .

### Launch the App

To launch the Flask App, run the following from the project repository root:

    python -m parkVar.main

The main python script expects the data and logs folders to be located at the repository root level, running the app from a different location may cause errors.

If you encounter the error "ModuleNotFoundError: No module names 'parkVar'" ensure you are running the main script from the repository root, if the error continues try installing editable to ensure the package is on the path (see previous section).

## Docker installation

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


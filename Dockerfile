# syntax=docker/dockerfile:1

# Compile assets
FROM node:14-alpine AS assets

WORKDIR /application/
COPY package.json package-lock.json webpack.config.js tsconfig.json \
    /application/
RUN npm install -g npm@latest && npm i

COPY ./scripts /application/scripts
COPY ./ts2-web /application/ts2-web
RUN NODE_ENV=production npm run build && \
    npm prune --production

# Setup environment
FROM --platform=linux/amd64 python:3.9-slim-buster AS runtime

RUN apt-get update && \
    apt-get -y install libmemcached-dev gcc zlib1g-dev && \
    apt-get clean

# Setup environment
ENV POETRY_VERSION=1.1.7 \
    PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

WORKDIR /application/
COPY pyproject.toml poetry.lock /application/

RUN python3 -m pip install -U poetry==$POETRY_VERSION
RUN python3 -m poetry install --no-dev --no-interaction --no-ansi

RUN apt-get -y purge gcc zlib1g-dev && \
    apt-get -y autoremove

RUN adduser -u 5555 --disabled-password --gecos "" ts2 && \
    chown -R ts2 /application
USER ts2

# Finalize file system
COPY --from=assets /application/build /application/build
COPY ./ /application/

SHELL [ "/bin/bash", "-c" ]

# Setup project
ENV DJANGO_SETTINGS_MODULE=ts2.conf.production \
    NLTK_DATA=/application/instance/nltk_data

RUN ./bin/setup
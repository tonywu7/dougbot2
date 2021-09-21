# syntax=docker/dockerfile:1

FROM python:3.9.6-buster AS build

# Prerequisites
RUN apt-get update && \
    apt-get -y install libmemcached-dev

# Setup environment
ENV POETRY_VERSION=1.1.7
RUN python3 -m pip install poetry==$POETRY_VERSION

WORKDIR /application/
COPY pyproject.toml poetry.lock /application/
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-dev --no-interaction --no-ansi

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
FROM python:3.9.6-slim-buster AS runtime

RUN apt-get update && \
    apt-get -y install libmemcached-dev

# Finalize file system
COPY --from=build /application/.venv /application/.venv
COPY --from=assets /application/build /application/build
RUN python3 -m venv /application/.venv
COPY ./ /application/

WORKDIR /application/
SHELL [ "/bin/bash", "-c" ]

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random

# Setup project
ENV DJANGO_SETTINGS_MODULE=ts2.conf.production
RUN ./bin/setup

RUN adduser -u 5555 --disabled-password --gecos "" ts2 && \
    chown -R ts2 /application
USER ts2
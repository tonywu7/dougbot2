# syntax=docker/dockerfile:1

FROM python:3.9.6-buster AS build

# Prerequisites
RUN apt-get update && \
    apt-get -y install libmemcached-dev

# Setup environment
ENV POETRY_VERSION=1.1.7
RUN python3 -m pip install poetry==$POETRY_VERSION

WORKDIR /application
COPY ./pyproject.toml ./poetry.lock /application/
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-dev --no-interaction --no-ansi

# Compile assets
FROM node:14-alpine AS assets

WORKDIR /application/ts2/web/bundle
COPY ./ts2/web/bundle/package.json \
    ./ts2/web/bundle/package-lock.json \
    ./ts2/web/bundle/webpack.config.js \
    /application/ts2/web/bundle/
RUN npm install -g npm@latest && npm i

COPY ./ts2/web/bundle/ /application/ts2/web/bundle/
RUN NODE_ENV=production npm run build && \
    npm prune --production

# Setup environment
FROM python:3.9.6-slim-buster AS runtime

RUN apt-get update && \
    apt-get -y install libmemcached-dev

# Finalize file system
COPY --from=assets /application /application
COPY --from=build /application/.venv /application/.venv
RUN python3 -m venv /application/.venv
COPY ./ /application/

WORKDIR /application
SHELL ["/bin/bash", "-c"]

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random

# Setup project
ENV DJANGO_SETTINGS_MODULE=ts2.settings.production
RUN NO_CACHE=true ./bin/setup

RUN adduser -u 5555 --disabled-password --gecos "" ts2 && \
    chown -R ts2 /application
USER ts2
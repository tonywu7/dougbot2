# syntax=docker/dockerfile:1

FROM continuumio/miniconda3 AS build

# Prerequisites
RUN apt-get update && \
    apt-get -y install linux-headers-amd64 build-essential
RUN conda install --override-channels -c main -c conda-forge conda-pack

# Setup conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Run conda-pack
RUN conda-pack -n ts2 -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar
RUN /venv/bin/conda-unpack

# Compile assets
FROM node:14-alpine AS assets

WORKDIR /application/ts2/web/bundle
COPY ./ts2/web/bundle/package.json \
    ./ts2/web/bundle/package-lock.json \
    ./ts2/web/bundle/webpack.config.js \
    /application/ts2/web/bundle/
RUN npm install -g npm@latest && npm i

COPY ./ts2/web/bundle/ /application/ts2/web/bundle/
RUN NODE_ENV=production npm run build && npm prune --production

WORKDIR /application
COPY . /application

# Initialize instance data
FROM debian:buster AS runtime

COPY --from=assets /application /application
COPY --from=build /venv /venv

SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=ts2.settings.production

WORKDIR /application
RUN NO_CACHE=true ./bin/setup

RUN adduser -u 5555 --disabled-password --gecos "" ts2 && chown -R ts2 /application
USER ts2
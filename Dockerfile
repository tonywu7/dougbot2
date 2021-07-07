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
RUN conda-pack -n telescope2 -o /tmp/env.tar && \
    mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
    rm /tmp/env.tar
RUN /venv/bin/conda-unpack

# Compile assets
FROM node:14-alpine AS assets

WORKDIR /application
COPY . /application

WORKDIR /application/telescope2/web/bundle
RUN npm install -g npm@latest && npm i && NODE_ENV=production npm run build && npm prune --production

# Initialize instance data
FROM debian:buster AS runtime

COPY --from=assets /application /application
COPY --from=build /venv /venv

SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=telescope2.settings.production

WORKDIR /application
RUN NO_CACHE=true ./bin/setup

RUN adduser -u 5555 --disabled-password --gecos "" telescope2 && chown -R telescope2 /application
USER telescope2
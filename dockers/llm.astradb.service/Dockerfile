# syntax=docker/dockerfile-upstream:master
# Adapted from: https://github.com/pytorch/pytorch/blob/master/Dockerfile
FROM python:3.11-slim as base-container

# Automatically set by buildx
ARG TARGETPLATFORM

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  ca-certificates \
  ccache \
  curl \
  libssl-dev ca-certificates make \
  git python3-pip && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /populateastradb

COPY populateastradb.py .
COPY pyproject.toml .

RUN --mount=type=cache,target=/root/.cache/pip \
  pip3 install -v --no-cache-dir \
  "langchain" "sentence-transformers" "lxml" "bs4" "astrapy" && \
  pip3 install --no-cache-dir -e .

CMD ["python", "populateastradb.py"]

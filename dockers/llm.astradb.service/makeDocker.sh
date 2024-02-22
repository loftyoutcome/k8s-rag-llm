#!/usr/bin/env bash
set -e

#set -x

POPULATE_ASTRA_DB_REPO=$1
POPULATE_ASTRA_DB_TAG=$2

echo ""
echo "Building docker for vectordb creation"
docker build --platform=linux/amd64 --load -f ./Dockerfile -t ${POPULATE_ASTRA_DB_REPO}:${POPULATE_ASTRA_DB_TAG} .
docker push ${POPULATE_ASTRA_DB_REPO}:${POPULATE_ASTRA_DB_TAG}

#!/usr/bin/env bash
set -e

#set -x

MODEL_NAMESPACE=$1

echo ""
echo "Deleting model namespace from all workload clusters"
kubectl delete namespace ${MODEL_NAMESPACE} --context=nova

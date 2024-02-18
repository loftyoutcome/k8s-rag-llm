#!/usr/bin/env bash
set -e

#set -x

MODEL_NAMESPACE=$1
DOCKER_CONFIG_JSON=$2
RUN_INGESTION=$3
MODEL_INGESTION_CLUSTER=$4
VECTOR_DB_INPUT_ARG=$5
VECTOR_DB_INPUT_TYPE=$6
VECTOR_DB_S3_FILE=$7
AWS_ACCESS_KEY_ID=$8
AWS_SECRET_ACCESS_KEY=$9

export MODEL_NAMESPACE
export DOCKER_CONFIG_JSON
export RUN_INGESTION
export MODEL_INGESTION_CLUSTER
export VECTOR_DB_INPUT_ARG
export VECTOR_DB_INPUT_TYPE
export VECTOR_DB_S3_FILE
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

######## SETUP
echo ""
echo "Placing model namespace and image pull secret on all workload clusters"
echo ">Applying SpreadAcrossAllClusters policy for namespace"
kubectl apply -f llm.deploy.setup/nspolicy.yaml --context=nova

echo ">Applying namespace using SpreadAcrossAllClusters policy"
envsubst < llm.deploy.setup/namespace.yaml | kubectl apply --context=nova -f -
sleep 30 # wait for namespace workload placement

echo ">Applying SpreadAcrossAllClusters policy for image pull secret"
kubectl apply -f llm.deploy.setup/secretpolicy.yaml --context=nova

echo ">Applying image pull secret using SpreadAcrossAllClusters policy"
envsubst < llm.deploy.setup/secret.yaml | kubectl apply --context=nova -f -
sleep 30 # wait for image pull secret workload placement

######## LLM-SERVING
echo ""
echo "Placing LLM-Serving w/LB on an LLM-Serving-Cluster w/adequate GPU"
echo ">Applying ChooseAvailableGPUCluster policy"
envsubst < llm.gpu.service/availablegpupolicy.yaml | kubectl apply --context=nova -f -

echo ">Applying deployment for llm serving on workload cluster with available gpu resource"
envsubst < llm.gpu.service/mptpluslb.yaml | kubectl apply --context=nova -f -

echo ">Waiting for deployment to be available"
kubectl wait --for=condition=available deployment/mpt7b-deployment --namespace ${MODEL_NAMESPACE} --timeout=15m --context=nova

echo ">Getting externalIP for LLM service"
LLMIP=`kubectl get services --namespace ${MODEL_NAMESPACE} mpt7b-service --output jsonpath='{.status.loadBalancer.ingress[0].hostname}' --context=nova`
echo ${LLMIP}

######## INGESTION
echo ""
if [ "${RUN_INGESTION}" = true ]; then
    echo "Placing VectorDB-Ingester job on VectorDB-Ingester-Cluster"
    echo ">Applying ChooseSpecificCluster policy for ${MODEL_INGESTION_CLUSTER}"
    envsubst < llm.vdb.service/specificclusterpolicy.yaml | kubectl apply --context=nova -f -

    echo ">Applying job for data ingestion, placed on specific cpu ingestion workload cluster"
    envsubst < llm.vdb.service/createvectordb.yaml | kubectl apply --context=nova -f -

    echo ">Waiting for job to complete"
    kubectl wait --for=condition=complete job/createvectordb --namespace ${MODEL_NAMESPACE} --timeout=15m --context=nova
else
    echo "Skipping placing VectorDB-Ingester job on VectorDB-Ingester-Cluster"
fi

######## LLM+RAG-SERVING
echo ""
echo "Placing LLM+RAG-Serving w/LB on all LLM+RAG-Serving-Clusters"
echo ">Applying SpreadAcrossSubsetClusters policy; has custom tag on non-GPU cluster for this subset"
envsubst < llm.rag.service/spreadacrossclusterset.yaml | kubectl apply --context=nova -f -

echo ">Applying deployment for rag serving, spread across workload cluster subset with specified label"
MODEL_LLM_SERVER_URL="http://"${LLMIP}
envsubst < llm.rag.service/serveragllmpluslb.yaml | kubectl apply --context=nova -f -

echo ">Waiting for deployment to be available"
kubectl wait --for=condition=available deployment/serveragllm-deployment --namespace ${MODEL_NAMESPACE} --timeout=15m --context=nova

echo ">Getting externalIPs for service"
sleep 30 # wait for externalIPs to be synced to Nova CP
RAGLLMIPLIST=`kubectl get services --namespace ${MODEL_NAMESPACE} serveragllm-service --output jsonpath='{.status.loadBalancer.ingress}' --context=nova`
echo ${RAGLLMIPLIST}

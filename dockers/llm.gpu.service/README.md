# k8s-rag-llm/dockers/llm.gpu.service
How to build docker for llm gpu service:

1 Run openllm build to create a bento

$ openllm build mosaicml/mpt-7b-chat --backend vllm --serialization legacy

Successfully built Bento 'mosaicml--mpt-7b-chat-service:df5a0d74bf7a93f8f76f64ae6b45e2b996ca4764'.

2 Create a docker container from the bento

$ bentoml containerize mosaicml--mpt-7b-chat-service:df5a0d74bf7a93f8f76f64ae6b45e2b996ca4764 --opt progress=plain --opt platform=linux/amd64

3 Tag and push the docker as elotl/mpt7bllm:v1.0

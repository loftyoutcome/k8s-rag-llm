from typing import Union
from fastapi import FastAPI

import os
import sys
import openai
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import AstraDB

########
# Get environment variables
astradb_app_token = os.environ.get('ASTRA_DB_APPLICATION_TOKEN')
if astradb_app_token is None:
    print("Please set environment variable ASTRA_DB_APPLICATION_TOKEN")
    sys.exit(1)
astradb_api_endpoint = os.environ.get('ASTRA_DB_API_ENDPOINT')
if astradb_api_endpoint is None:
    print("Please set environment variable ASTRA_DB_API_ENDPOINT")
    sys.exit(1)
astradb_collection = os.environ.get('ASTRA_DB_COLLECTION')
if astradb_collection is None:
    print("Please set environment variable ASTRA_DB_COLLECTION")
    sys.exit(1)

########
# Setup model name and query template parameters
model = "mosaicml--mpt-7b-chat"
template = """Answer the question based only on the following context:
{context}

Question: {question}
"""
os.environ["TOKENIZERS_PARALLELISM"] = "false"

########
# Get connection to LLM server
model_llm_server_url = os.environ.get('MODEL_LLM_SERVER_URL')
if model_llm_server_url is None:
    print("Please set environment variable MODEL_LLM_SERVER_URL")
    sys.exit(1)
llm_server_url = model_llm_server_url + '/v1'
client = openai.OpenAI(base_url=llm_server_url, api_key='na')

########
# Load vectorstore and get retriever for it
vectorstore = AstraDB(
    embedding=HuggingFaceEmbeddings(),
    collection_name=astradb_collection,
    api_endpoint=astradb_api_endpoint,
    token=astradb_app_token,
    namespace="default_keyspace",
)

########
# Fetch RAG context for question, form prompt from context and question, and call model
def get_answer(question: Union[str, None]):
    docs = vectorstore.similarity_search(question)
    promptstr = template.format(context=docs[0].page_content, question=question)
    completions = client.completions.create(prompt=promptstr, model=model, max_tokens=64, temperature=0.1)
    print("Question: ", question)
    print("Completions: ", completions)
    answer = completions.choices[0].text + "\n"
    return answer

########
# Start API service to answer question
app = FastAPI()
@app.get("/answer/{question}")
def read_item(question: Union[str, None] = None):
    answer = get_answer(question)
    return {"question": question, "answer": answer}

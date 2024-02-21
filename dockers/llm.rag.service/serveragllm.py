from typing import Union
from fastapi import FastAPI

import os
import sys
import openai
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import boto3
import pickle
import time

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
vectordb_bucket = "faiss-vectordbs"
vectordb_key = os.environ.get('VECTOR_DB_S3_FILE')
if vectordb_key is None:
    print("Please set environment variable VECTOR_DB_S3_FILE")
    sys.exit(1)
s3_client = boto3.client('s3')
response = s3_client.get_object(Bucket=vectordb_bucket, Key=vectordb_key)
print(response)
body = response['Body'].read()
vectorstore = pickle.loads(body)
retriever = vectorstore.as_retriever()
time.sleep(30)

########
# Fetch RAG context for question, form prompt from context and question, and call model
def get_answer(question: Union[str, None]):
    docs = retriever.get_relevant_documents(question)
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

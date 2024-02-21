import os
import sys

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders.sitemap import SitemapLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

import boto3
import pickle

vectordb_bucket = "faiss-vectordbs"

vectordb_key = os.environ.get('VECTOR_DB_S3_FILE')
if vectordb_key is None:
    print("Please set environment variable VECTOR_DB_S3_FILE")
    sys.exit(1)

vectordb_input_type = os.environ.get('VECTOR_DB_INPUT_TYPE')
if vectordb_input_type is None:
    print("Please set environment variable VECTOR_DB_INPUT_TYPE")
    sys.exit(1)

vectordb_input_arg = os.environ.get('VECTOR_DB_INPUT_ARG')
if vectordb_input_arg is None:
    print("Please set environment variable VECTOR_DB_INPUT_ARG")
    sys.exit(1)

# Initialize vectorstore and create pickle representation
os.environ["TOKENIZERS_PARALLELISM"] = "false"
if vectordb_input_type == 'text':
    vectorstore = FAISS.from_texts(vectordb_input_arg, embedding=HuggingFaceEmbeddings())
elif vectordb_input_type == 'sitemap':
    sitemap_loader = SitemapLoader(web_path=vectordb_input_arg, filter_urls=["^((?!.*/v.*).)*$"])
    sitemap_loader.requests_per_second = 1
    docs = sitemap_loader.load()
    print("Count of sitemap docs loaded:", len(docs))
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,
        chunk_overlap  = 100,
        length_function = len,
    )
    texts = text_splitter.split_documents(docs)
    vectorstore = FAISS.from_documents(texts, embedding=HuggingFaceEmbeddings())
else:
    print("Unknown value for VECTOR_DB_INPUT_TYPE:", vectordb_input_type)
    sys.exit(1)

pickle_byte_obj = pickle.dumps(vectorstore)

# Persist vectorstore to S3 bucket vectorstores
s3_client = boto3.client('s3')
s3_client.put_object(Body=pickle_byte_obj, Bucket=vectordb_bucket, Key=vectordb_key)
print("Uploaded vectordb to", vectordb_bucket, vectordb_key)
sys.exit(0)

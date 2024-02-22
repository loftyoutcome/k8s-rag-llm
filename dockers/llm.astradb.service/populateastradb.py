import os
import sys

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import AstraDB
from langchain_community.document_loaders.sitemap import SitemapLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

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
vectordb_input_type = os.environ.get('VECTOR_DB_INPUT_TYPE')
if vectordb_input_type is None:
    print("Please set environment variable VECTOR_DB_INPUT_TYPE")
    sys.exit(1)
vectordb_input_arg = os.environ.get('VECTOR_DB_INPUT_ARG')
if vectordb_input_arg is None:
    print("Please set environment variable VECTOR_DB_INPUT_ARG")
    sys.exit(1)

# Initialize the astradb vector store
vectorstore = AstraDB(
    embedding=HuggingFaceEmbeddings(),
    collection_name=astradb_collection,
    api_endpoint=astradb_api_endpoint,
    token=astradb_app_token,
    namespace="default_keyspace",
)

# Ingest data, apply embeddings, and store data
os.environ["TOKENIZERS_PARALLELISM"] = "false"
if vectordb_input_type == 'sitemap':
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
    inserted_ids = vectorstore.add_documents(texts)
    print("Count of inserted records:", len(inserted_ids))
else:
    print("Unknown value for VECTOR_DB_INPUT_TYPE:", vectordb_input_type)
    sys.exit(1)

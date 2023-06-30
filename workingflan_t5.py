import os
from langchain import HuggingFaceHub
from langchain.embeddings import HuggingFaceHubEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chains import VectorDBQA
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains.question_answering import load_qa_chain
from flask import Flask, render_template, request, redirect
from pymongo import MongoClient

app = Flask(__name__)

#gvijaya5
#task2
os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

directory = r'C:\Users\gokul\OneDrive\Desktop\Fourth Square\Interview 2\Docs'

url = "mongodb+srv://gvijaya5:task2@cluster0.kkkewow.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(url)
db = client['QA']
collection = db['QA']

def load_docs(directory):
  loader = DirectoryLoader(directory)
  documents = loader.load()
  return documents

def split_docs(documents,chunk_size=1000,chunk_overlap=20):
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
  docs = text_splitter.split_documents(documents)
  return docs

def finddocs(query):
  num = 2
  matching_docs = db.similarity_search(query,num)
  return matching_docs

def save_query_answer(query, answer):
    query_answer_data = {"query": query, "answer": answer}
    collection.insert_one(query_answer_data)

flan_ul2 = HuggingFaceHub(repo_id="google/flan-t5-xxl")
embeddings = HuggingFaceHubEmbeddings()

documents = load_docs(directory)
docs = split_docs(documents)
db = Chroma.from_documents(docs, embeddings)

query = "How can I cancel"
matchingdocs = finddocs(query)

chain = load_qa_chain(flan_ul2, chain_type = "stuff")
answer = chain.run(input_documents=matchingdocs, question=query)
print(answer)
save_query_answer(query, answer)

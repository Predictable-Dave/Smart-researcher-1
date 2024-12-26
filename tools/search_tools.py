import json
import requests
import os
import http.client
from crewai.tools import tool
import logging
import logging.handlers
from typing import Dict, Any, Optional, Union, Type
from pydantic import Field, BaseModel, create_model
from tavily import TavilyClient
import chromadb
from db_utils import get_vector_db_file, get_next_id, store_result, get_result_by_id,similarity_threshold

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/dummy_tool.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


class SearchTools:
    """Collection of search tools for information retrieval."""

    serper_api_key = os.getenv("SERPER_API_KEY")

    @tool("Simple Google Search")
    def search_internet_with_google(question: str) -> list:
        """Search the internet using Google for articles about a question."""
        # Tool logic here
        try:
          data=json.loads(question)
          q=data.get('question',{})  
        except ValueError as e:
          q=question

        tag="GoogleSearch"
        cache_query=f'{tag}:{q}'
        chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
        # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
        collection = chroma_client.get_or_create_collection(name="cached_docs")
        cached_result = collection.query(
          query_texts=[cache_query], # Chroma will embed this for you
          n_results=1 # how many results to return
      )
        if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
          doc_id=cached_result['ids'][0][0]
          data=get_result_by_id(doc_id)
          logger.info(f'Cache hit for Google search {doc_id}')
        else: 
          serper_api_key = os.getenv("SERPER_API_KEY")
          conn = http.client.HTTPSConnection("google.serper.dev")
          payload = json.dumps({
            "q": q,
            "num": 10
          })
          headers = {
            'X-API-KEY': serper_api_key,
            'Content-Type': 'application/json'
          }
          conn.request("POST", "/search", payload, headers)
          res = conn.getresponse()
          results = res.read()
          data = [" ".join(result.decode("utf-8")['organic']) for result in results]
          data = data if data else "No results found"

          id = get_next_id()
          collection.upsert(
              documents=[cache_query],
              ids=[f'id{id}'],
          )
          test = collection.query(
              query_texts=[cache_query], # Chroma will embed this for you
              n_results=3 # how many results to return
          )
          logger.info(f'Cached updated mosts similar documents {test}')
          store_result(id,q,data)

        return json.loads(data)

    @tool("Simple Google News Search")
    def search_news_with_google(question: str) -> list:
        """Search the internet using Google for articles about a question."""
        # Tool logic here
        try:
          data=json.loads(question)
          q=data.get('question',{})  
        except ValueError as e:
          q=question

        tag="GoogleNews"
        cache_query=f'{tag}:{q}'
        chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
        # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
        collection = chroma_client.get_or_create_collection(name="cached_docs")
        cached_result = collection.query(
          query_texts=[cache_query], # Chroma will embed this for you
          n_results=1 # how many results to return
        )
        if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
          doc_id=cached_result['ids'][0][0]
          data=get_result_by_id(doc_id)
        else: 
          serper_api_key = os.getenv("SERPER_API_KEY")
          conn = http.client.HTTPSConnection("google.serper.dev")
          payload = json.dumps({
            "q": q,
            "num": 10
          })
          headers = {
            'X-API-KEY': serper_api_key,
            'Content-Type': 'application/json'
          }
          conn.request("POST", "/news", payload, headers)
          res = conn.getresponse()
          data = res.read()

          id = get_next_id()
          collection.upsert(
            documents=[cache_query],
            ids=[f'id{id}'],
          )
          store_result(id,q,data)

        return json.loads(data.decode("utf-8"))['organic']

    @tool("Tavily Search")
    def TavilySearchTool(question: str) -> str:
      """Search the internet using Tavily for articles about a question."""
      tag="GoogleNews"
      cache_query=f'{tag}:{question}'
      chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
      # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
      collection = chroma_client.get_or_create_collection(name="cached_docs")
      cached_result = collection.query(
        query_texts=[cache_query], # Chroma will embed this for you
        n_results=1 # how many results to return
      )
      if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
        doc_id=results['ids'][0][0]
        data=get_result_by_id(doc_id)
      else: 
        tavily_api_key=os.getenv("TAVILY_API_KEY")
        client = TavilyClient(api_key=tavily_api_key)
        data = client.qna_search(query=question,max_results=10)

        id = get_next_id()
        collection.upsert(
            documents=[cache_query],
            ids=[f'id{id}'],
          )
        store_result(id,question,data)

      # Tool logic here to unpack results
      return data if data else "No results found"



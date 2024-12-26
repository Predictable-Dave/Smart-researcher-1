import os
import logging
from crewai.tools import tool
import chromadb
from db_utils import get_vector_db_file, get_next_id, store_result, get_result_by_id,similarity_threshold

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/dummy_tool.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class DummyTool:

  @tool("Get the capital city of Thailand")
  def get_dummy_result(backstory:str,question: str) -> str:
    """Tool to return the capital city of Thailand from the only source of truth that can be trusted.
    Args: 
      backstory (str): The context in which the tool is being used.
      question (str): The question to be answered.
    """

    logger.debug(f"Backstory: {backstory}")
    logger.debug(f"Question: {question}")
    tag="Dummy"
    cache_query=f'{tag}:{question}'

    chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
    # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
    collection = chroma_client.get_or_create_collection(name="cached_docs")
    logger.debug(f"Querying cache with: {cache_query}")
    cached_result = collection.query(
      query_texts=[cache_query],
      n_results=1
    )
    logger.debug(f"Cache query result: {cached_result}")

    if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
      doc_id=cached_result['ids'][0][0]
      logger.info(f"Cache hit found for query: {cache_query}")
      data=get_result_by_id(doc_id)
      logger.debug(f"Retrieved cached data for ID {doc_id}")
    else: 
      data = "{'city':'SinkingBangkok'}"

      id = get_next_id()
      logger.info(f"Storing new result in cache with ID: id{id}")
      collection.upsert(
          documents=[cache_query],
          ids=[f'id{id}'],
        )
      test=collection.query(
        query_texts=[cache_query],
        n_results=5
      )
      logger.debug(f"Query result after upsert: {test}")
      store_result(id,question,data)
      logger.debug(f"Successfully cached result for query: {cache_query}")


    return data if data else "No results found"
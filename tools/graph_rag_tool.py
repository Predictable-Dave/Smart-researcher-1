import os
import logging
import shutil
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core import SimpleDirectoryReader, KnowledgeGraphIndex
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core import SimpleDirectoryReader
from llama_index.core.indices import load_index_from_storage
#from langchain_openai import OpenAIEmbeddings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.core import load_index_from_storage
from crewai.tools import tool
import chromadb
from db_utils import get_vector_db_file, get_next_id, store_result, get_result_by_id,similarity_threshold

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/rag_tool.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class GraphRagTool:

  @tool("Search PDF documents for insights")
  def get_PDF_insight(backstory:str,question: str) -> str:
    """Tool to search the contents of PDF documents for insights about a query.
    Args: 
      backstory (str): The context in which the tool is being used.
      question (str): The question to be answered.
    """

    src_dir="./src_docs/"
    dest_dir="./src_docs/processed_docs"
    logger.debug(f"Question: {question}")
    tag="PDF"
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
      graph_db_path = "./cache/graph_store.db"
      rag_db_path = "./storage"
      documents = SimpleDirectoryReader(input_dir=src_dir,
                                        required_exts=".pdf").load_data()
      graph_db_path = "./store/graph_store.db"

      openai_api_key = os.environ.get('OPENAI_API_KEY', 'dev-key-please-change')
      openai_model_name = os.environ.get('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')

      llm = OpenAI(
        model=openai_model_name,
        temperature=0.5,
        api_key=openai_api_key,
      )
      #embeddings = OpenAIEmbeddings(api_key=openai_api_key)
      embed_model = OpenAIEmbedding(api_key=openai_api_key,
                                  model="text-embedding-3-small",
                                  embed_batch_size=100)
      Settings.embed_model = embed_model
      Settings.chunk_size = 256
      Settings.llm = llm
      if os.path.exists(rag_db_path):
                                               graph_store = SimpleGraphStore.from_persist_path(graph_db_path)
                                               storage_context = StorageContext.from_defaults(
                                               docstore=SimpleDocumentStore.from_persist_dir(persist_dir=rag_db_path),
                                               vector_store=SimpleVectorStore.from_persist_dir(
                                               persist_dir=rag_db_path
                                               ),
                                               index_store=SimpleIndexStore.from_persist_dir(persist_dir=rag_db_path),
                                               graph_store=SimpleGraphStore.from_persist_dir(rag_db_path)
                                               )
                                               index = load_index_from_storage(storage_context)

      else:
                                               graph_store = SimpleGraphStore()
                                               storage_context = StorageContext.from_defaults(graph_store=graph_store)
                                               index = KnowledgeGraphIndex.from_documents(
                                                                                          documents=documents,
                                                                                          max_triplets_per_chunk=3,
                                                                                          storage_context=storage_context,
                                                                                          embed_model=embed_model,
                                                                                          include_embeddings=True)

      graph_store.persist(graph_db_path)
      storage_context.persist("./storage")
      query_engine = index.as_query_engine(llm=llm, similarity_top_k=5)

      question = backstory
      data = query_engine.query(question)


      id = get_next_id()
      logger.info(f"Storing new result in cache with ID: id{id}")
      collection.upsert(
          documents=[cache_query],
          ids=[f'id{id}'],
        )
      store_result(id,question,data)
      logger.debug(f"Successfully cached result for query: {cache_query}")

    if not os.path.exists(dest_dir):
      os.makedirs(dest_dir)

    for filename in os.listdir(src_dir):
      if filename.endswith(".pdf"):
        source_file = os.path.join(src, filename)
        dest_file = os.path.join(dest_dir, filename)
        shutil.move(source_file, dest_file)


    return data if data else "No results found"
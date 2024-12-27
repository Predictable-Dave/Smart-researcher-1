import json
import logging
import os
import shutil

import chromadb
import faiss
from crewai.tools import tool
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from llama_index.core import StorageContext
from llama_index.core.indices import load_index_from_storage
from llama_index.core.indices.vector_store.base import VectorStoreIndex
from llama_index.core.node_parser import MarkdownElementNodeParser
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_parse import LlamaParse, ResultType
from pydantic.v1 import NoneBytes

from db_utils import (
  db_path,
  get_next_id,
  get_result_by_id,
  similarity_threshold,
  store_result,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs/excel_rag.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

directory_path = "./src_docs"
processed_path = "./src_docs/processed_docs"
excel_rag_db = "./cache/excel_rag_db.db"

class ExcelRagTool:
  def iterate_excel_files(directory):
    """Iterates through Excel files in a given directory."""
    logger.info(f"Scanning directory {directory} for Excel files")
    for filename in os.listdir(directory):
        if filename.endswith(('.xls', '.xlsx', '.xlsm')):
            filepath = os.path.join(directory, filename)
            try:
                logger.debug(f"Found Excel file: {filepath}")
                yield filepath
            except Exception as e:
                logger.error(f"Error reading {filepath}: {str(e)}")

  def extract_text_from_excel_llama_parse(excel_file):
    logger.info(f"Extracting text from {excel_file}")
    llamaparse_api_key = os.environ.get('LLAMAPARSE_API_KEY','dummy value')
    parser = LlamaParse(
        api_key=llamaparse_api_key,
        parsing_instruction = """You are parsing an analyst report of year on year sector growth by region.
           break out results, by region and sectors.
           if a worksheeted call Definitions or synonym is used parse this first and use the categories and the definitions associated to structe the analysis with the context of regions and sectors.
        """,
        result_type="markdown",
    )
    try:
        docs = parser.load_data(excel_file)
        logger.debug(f"Successfully extracted {len(docs)} documents")
        return docs
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise

  def _interogate_excel_rag(prompt:str, question:str):
        tag = "ExcelRAG"
        cache_query = f'{tag}:{question}'

        try:
            chroma_client = chromadb.PersistentClient(path=db_path)
            collection = chroma_client.get_or_create_collection(name="cached_docs")
            cached_result = collection.query(
                query_texts=[cache_query],
                n_results=1
            )
            logger.debug(f"Cache query result: {cached_result}")

            if cached_result['distances'] and len(cached_result['distances'][0]) > 0 and cached_result['distances'][0][0] < similarity_threshold():
                logger.info("Cache hit found")
                doc_id = cached_result['ids'][0][0]
                data = get_result_by_id(doc_id)
                return data if data else "No results found"

        except Exception as e:
            logger.error(f"Error in cache lookup: {str(e)}")

        logger.info("No cache hit, processing query")
        try:
            openai_api_key = os.environ.get('OPENAI_API_KEY', 'dev-key-please-change')
            openai_model_name = os.environ.get('OPENAI_MODEL_NAME', 'gpt-3.5-turbo')

            llm = ChatOpenAI(
                model=openai_model_name,
                temperature=0.5,
                api_key=openai_api_key,
            )
            embeddings = OpenAIEmbeddings(api_key=openai_api_key)

            logger.debug("Creating FAISS index")
            index = faiss.IndexFlatL2(len(embeddings.embed_query("hello world")))
            vectorstore = FAISS(
                embedding_function=embeddings,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = []

            logger.info("Processing Excel files")
            for filepath in ExcelRagTool.iterate_excel_files(directory_path):
                logger.debug(f"Processing file: {filepath}")
                docs = ExcelRagTool.extract_text_from_excel_llama_parse(filepath)
                for doc in docs:
                    texts.extend(text_splitter.split_text(doc.text))
                shutil.move(filepath, processed_path)

            logger.debug(f"Created {len(texts)} text chunks")
            temp_vectorstore = FAISS.from_texts(texts, embeddings)

            if os.path.exists(excel_rag_db):
                logger.info("Loading existing vector store")
                vectorstore.load_local(excel_rag_db, embeddings, allow_dangerous_deserialization=True)
                vectorstore.merge_from(temp_vectorstore)
            else:
                logger.info("Creating new vector store")
                vectorstore = temp_vectorstore

            vectorstore.save_local(excel_rag_db)
            prompt_decorator = """

            Context: {context}

            Chat History: {chat_history}

            Question: {question}

            Answer:"""


            custom_prompt = ChatPromptTemplate.from_template(prompt.join(prompt_decorator))
            qa_chain = ConversationalRetrievalChain.from_llm(
                llm,
                retriever=vectorstore.as_retriever(),
                memory=memory,
                combine_docs_chain_kwargs={"prompt": custom_prompt}
            )

            logger.info("Executing query")
            response = qa_chain.invoke({"question": q})
            data = response['text']

            logger.debug("Storing result in cache")
            id = get_next_id()
            collection.upsert(
                documents=[cache_query],
                ids=[f'id{id}'],
            )
            store_result(id, question, data)

            return data

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return "An error occurred while processing the query"

  @tool("Get information about data centres from Excel files")
  def query_data_centre_src(question: str) -> str:
      """Tool to return information about data centres inculding ownership / shareholding,
      location, capacity in MW, and services like colocation and cloud storage.
      the sources used are highly trusted.
      Args: 
        question (str): The question to be answered.
      """
      logger.info(f"Executing data centre Excel query: {question}")
      context_template="""You are an industry researcher specialised in research on data centres, having unique to privileged industry sources. """

      return ExcelRagTool._interogate_excel_rag(context_template, question)

  @tool("Get highly factual information from Excel files")
  def query_excel_src(backstory: str, question: str) -> str:
    """Tool to return information about data centers, including ownership/shareholding,
       location, capacity in MW, and services like colocation and cloud storage.
       Data sources are highly trusted Excel files.

    Args:
        backstory (str): The context in which the tool is being used.
        question (str): The question to be answered about data centers.

    Returns:
        str: The answer to the question extracted from the Excel files,
              or an informative message if no answer is found.
    """

    logger.info(f"Excel query: Question: {question}")
    logger.debug(f"Backstory: {backstory}")

    return ExcelRagTool._interogate_excel_rag(backstory, question)


  @tool("Get Analyst insights Excel files. these are highly trusted sources")
  def query_excel_rag(description: str):
        """Tool to return information from market reports by region and category.
           Data sources are highly trusted Excel files.
    
        Args:
            tool_input (str): a json str containing the following keys and associated values:
                description(str): The backstory to the research
                context(str): The context in which the tool is being used.
                query (str): The question to be answered.
    
        Returns:
            str: The answer to the question extracted from the Excel files,
                  or an informative message if no answer is found.
        """
        # Tool logic here
        logger.info(f"Executing Excel RAG query: query_excel_rag({description})")    
        try:
          data=json.loads(description)
          backstory=data.get('description','general market research')
          context=data.get('context','no context provided')
          query=data.get('query','nothing to ask')  
          logger.info(f"Executing Excel RAG query: {query} with backstory {backstory} and context {context}")
        except ValueError as e:
          query=description
          backstory=context='general market research'

        logger.info(f"Executing Excel RAG query: {query}")
        tag = "ExcelRAG"
        cache_query = f'{tag}:{query}'
        persist_dir = "./cache/excel_storage"
        
        try:
            cache=chroma_client = chromadb.PersistentClient(path=db_path)
            cache_collection = chroma_client.get_or_create_collection(name="cached_docs")
            cached_result = cache_collection.query(
                query_texts=[cache_query],
                n_results=1
            )
            logger.debug(f"Cache query result: {cached_result}")
    
            if cached_result['distances'] and len(cached_result['distances'][0]) > 0 and cached_result['distances'][0][0] < similarity_threshold():
                logger.info("Cache hit found")
                doc_id = cached_result['ids'][0][0]
                data = get_result_by_id(doc_id)
                return data if data else "No results found"
    
        except Exception as e:
            logger.error(f"Error in cache lookup: {str(e)}")
    
        logger.info("No cache hit, processing query")
        
        model_name=os.getenv("OPENAI_MODEL_NAME","gpt-4o-mini")
        llm = OpenAI(model=model_name)
        #EMBEDDING_MODEL = "text-embedding-3-small"
        directory=directory_path
        logger.info(f"Processing Excel files")
        collection_name="excel_rag"
        llamaparse_api_key=os.getenv('LLAMAPARSE_API_KEY', 'dev-key-please-change')
        excel_files = [os.path.join(directory_path,filename) for filename in os.listdir(directory_path) if filename.endswith('.xlsx')]
        logger.debug(f"Excel files found: {excel_files}")
        chroma_client = chromadb.PersistentClient("./cache/excel_chroma_db")
        chroma_collection = chroma_client.get_or_create_collection(name=collection_name)
        parser_instruction=f"You are parsing an analyst report {backstory}. Extract information about {context} per geographic region"
        logger.info(f"processing with{parser_instruction}")
        parser = LlamaParse(
          api_key=llamaparse_api_key,
          parsing_instruction = parser_instruction,
          result_type=ResultType.MD
        )
        node_parser = MarkdownElementNodeParser(llm=llm, num_workers=4)
        if os.path.exists(os.path.join(persist_dir, "docstore.json")) and len(excel_files)>0:
           logger.info("Loading existing vector store")
           vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
           storage_context = StorageContext.from_defaults(persist_dir=persist_dir,vector_store=vector_store)
           storage_context.index_store.index_structs()
           recursive_index=load_index_from_storage(storage_context)
        else:
           logger.info("Creating new or updating vector store")
           vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
           storage_context = StorageContext.from_defaults(
              vector_store=vector_store,
           )
           excel_files = [os.path.join(directory,filename) for filename in os.listdir(directory) if filename.endswith('.xlsx')]
           if len(excel_files) > 0:
                logger.info(f"Processing {len(excel_files)} Excel files")
                documents=parser.load_data(excel_files)
                nodes = node_parser.get_nodes_from_documents(documents)
                base_nodes, objects = node_parser.get_nodes_and_objects(nodes)
                logger.info(f"Processing {len(base_nodes)} base nodes")
                recursive_index = VectorStoreIndex(nodes=base_nodes + objects, llm=llm,storage_context=storage_context)
                recursive_index.storage_context.persist(persist_dir=persist_dir)
                for excel_file in excel_files:
                    processed_filepath = os.path.join(processed_path, excel_file)
                    logger.info(f"Processing file: {excel_file}")
                    shutil.move(excel_file, processed_filepath)
           else:
            return "No excel files found"
    
        recursive_query_engine = recursive_index.as_query_engine(
            similarity_top_k=5, 
            llm=llm
        )
    
        response_recursive = recursive_query_engine.query(query)
    
        return response_recursive.response
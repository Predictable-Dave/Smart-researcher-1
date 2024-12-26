import os
from exa_py import Exa
from crewai.tools import tool
from db_utils import get_vector_db_file, get_next_id, store_result, get_result_by_id,similarity_threshold
import chromadb
class ExaSearchTool:


  @tool("Exa search and get contents")
  def search_and_get_contents_tool(question: str) -> str:
    """Tool using Exa's Python SDK to run semantic search and return result highlights."""

    tag="ExaSearch"
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
      exa_api_key = os.getenv("EXA_API_KEY")
      exa = Exa(exa_api_key)

      response = exa.search_and_contents(
          question,
          type="neural",
          use_autoprompt=True,
          num_results=10,
          highlights=True
      )

      response_results=enumerate(response.results)


      data= ''.join([f'<Title id={idx}>{eachResult.title}</Title>'+
                             f'<URL id={idx}>{eachResult.url}</URL>'+
                             f'<Highlight id={idx}>{eachResult.highlights}</Highlight>' 
                             for (idx, eachResult) in response_results])

      id = get_next_id()
      collection.upsert(
          documents=[cache_query],
          ids=[f'id{id}'],
        )
      store_result(id,question,data)


    return data if data else "No results found"
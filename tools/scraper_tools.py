from crewai.tools import tool
from firecrawl import FirecrawlApp
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List

import os
from db_utils import get_vector_db_file, get_next_id, store_result, get_result_by_id,similarity_threshold


class CompanyOverviewExtractSchema(BaseModel):
    company_mission: str
    products: List[str]
    services: List[str]
    locations: List[str]


class DataCenterProfile(BaseModel):
    name: str
    location: str
    operational_status: bool
    mw: int

class DataCentersExtractSchema(BaseModel):
    data_centers: List[DataCenterProfile]



# Initialize the FirecrawlApp with your API key
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=firecrawl_api_key)

class WebScrappingTools:

    @tool("Extract Company Overview and its products, services and locations")
    def extract_company_overview(url: str) -> CompanyOverviewExtractSchema:
        """Extracts company overview, products, services and locations from a given URL."""
        tag="ScrapeCompany"
        cache_query=f'{tag}:{url}'
        chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
          # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
        collection = chroma_client.get_or_create_collection(name="cached_docs")
        cached_result = collection.query(
            query_texts=[cache_query], # Chroma will embed this for you
            n_results=1 # how many results to return
        )
        if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
            doc_id=results['ids'][0][0]
            company_data=get_result_by_id(doc_id)
        else: 
            company_data = app.scrape_url(url, {
                'formats': ['extract'],
                'extract': {
                    'schema': CompanyOverviewExtractSchema.model_json_schema(),
                }
            })

            id = get_next_id()
            collection.upsert(
                documents=[cache_query],
                ids=[f'id{id}'],
              )
            store_result(id,url,data)
            
        return company_data

    @tool("Extract Company Overview and its products, services and locations")
    def extract_data_centre_key_facts(url: str) -> CompanyOverviewExtractSchema:
        """Extracts key facts about data centres from a given URL."""

        tag="ScrapeDataCentre"
        cache_query=f'{tag}:{url}'
        chroma_client = chromadb.PersistentClient(path=get_vector_db_file())
          # switch `create_collection` to `get_or_create_collection` to avoid creating a new collection every time
        collection = chroma_client.get_or_create_collection(name="cached_docs")
        cached_result = collection.query(
            query_texts=[cache_query], # Chroma will embed this for you
            n_results=1 # how many results to return
        )
        if cached_result['distances'][0] and cached_result['distances'][0][0]<similarity_threshold():
            doc_id=results['ids'][0][0]
            data_centres=get_result_by_id(doc_id)
        else: 

            data_centres = app.scrape_url(url, {
                'formats': ['extract'],
                'extract': {
                    'schema': DataCentersExtractSchema.model_json_schema(),
                }
            })


            id = get_next_id()
            collection.upsert(
                documents=[cache_query],
                ids=[f'id{id}'],
              )
            store_result(id,url,data_centres)

        return data_centres
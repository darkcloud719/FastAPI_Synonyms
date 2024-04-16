from fastapi import FastAPI, Path, HTTPException
from typing import List
from pydantic import BaseModel, Field , constr, field_validator
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SynonymMap
from azure.search.documents import SearchClient
from collections import OrderedDict
from dotenv import load_dotenv 
from rich import print as pprint
import os  
import logging

# Set the logging level to INFO
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Create a console handler and print log message to the console
console_handler = logging.StreamHandler()
# Set the level of the console handler to INFO
console_handler.setLevel(logging.INFO)
# Set the foramt
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# Add the console handler to the logger
logging.getLogger().addHandler(console_handler)

app = FastAPI()

class SynonymData(BaseModel):
    indexName: str
    mapName: constr(min_length=1 , max_length=10)
    synonymKeyValue: List[dict] = []

    @field_validator("synonymKeyValue")
    def check_synonym_key_value(cls, v):
        if not v or len(v) < 1:
            logging.error("SynonymKeyValue cannot be empty")
            raise ValueError("SynonymKeyValue cannot be empty")
        for item in v:
            if not isinstance(item, dict) or not item:
                logging.error("SynonymKeyValue should contain at least one non-empty directory")
                raise ValueError("SynonymKeyValue should contain at least one non-empty dictionary")
        return v
    
    @field_validator("mapName")
    def check_mapName(cls, v):
        if v != v.lower():
            logging.error("MapName should be in Lowercase")
            raise ValueError("MapName should be in Lowercase")
        return v

    # class Config:
    #     validate_assignment = True

class ReadSynonymData(BaseModel):
    mapName: constr(to_lower=True)
    synonymKeyValue: List[dict] = []

class DeleteSynonymData(BaseModel):
    indexName: str
    mapName: constr(to_lower=True)

# Define ResponseModel with data attribute as Field
class ResponseModel(BaseModel):
    code: int
    message: str
    data: List[SynonymData] | List[ReadSynonymData] = []

# Define status codes
status_codes = {
    200: "Success",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    415: "Unsupported Media Type",
    422: "Unprocessable Entity",
    500: "Internal Server Error"
}

# Endpoint to get all synonyms by indexName
@app.get("/get-all-synonymmaps")
def get_all_synonymmaps():
    try:
        global search_index_client
        # Retrieve all synonym maps
        synonymMapList = search_index_client.get_synonym_maps()
        # Extract names of synonym maps
        names = [synonymMap.name for synonymMap in synonymMapList]
        # print(names)
        # Initialize response object
        response = ResponseModel(code=200, message=status_codes.get(200))
        # Iterate over each synonym map
        for i, name in enumerate(names):
            # Add synonym map to response data
            response.data.append(ReadSynonymData(mapName=name, data=[]))
            # Retrieve details of the synonym map
            synonymMap = search_index_client.get_synonym_map(name)
            # Iterate over each synonym in the synonym map
            for j, synonym_format_str in enumerate(synonymMap.synonyms):
                # Extract destination synonym word and source synonym word list
                destination_synonym_str = synonym_format_str.split("=>")[1].strip()
                source_synonym_str_list = [element.strip() for element in synonym_format_str.split("=>")[0].split(",")]
                # Add synonym mapping to response data
                response.data[i].synonymKeyValue.append({destination_synonym_str: source_synonym_str_list})
        return response
    except Exception as e:
        # Handle exceptions and return error response
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e))
        return error_response
    
# Endpoint of get synonym map by Azure search index name
@app.get("/get-synonymmap-by-aisearchindexname/{indexName}")
def get_synonymmap_by_aisearchindexname(indexName: str):
    global search_index_client
    try:
        # Initialize Azure Search Index Client
        index = search_index_client.get_index(indexName)
        temp_list = []
        synonymNameMappingList = []

        # retrieve synonym maps associated with the index
        for i, field in enumerate(index.fields):
            if field.synonym_map_names is not None and len(field.synonym_map_names) > 0:
                for synonymMapData in field.synonym_map_names:
                    temp_list.append(synonymMapData)
        # Remove duplicates from the list of synonym map names
        # temp_list = list(set(temp_list))
        temp_list = list(OrderedDict.fromkeys(temp_list))

        # If synonym maps exists, retrieve their details
        if(len(temp_list)>0):
            for i, name in enumerate(temp_list):
                synonymNameMappingList.append(search_index_client.get_synonym_map(name))

        # Create response model and populate with synonym map details
        response = ResponseModel(code=200, message=status_codes.get(200))
        for i, synonymNameMapping in enumerate(synonymNameMappingList):
            response.data.append(SynonymData(indexName=indexName, mapName=synonymNameMapping.name, data=[]))
            for synonym in synonymNameMapping.synonyms:
                synonym_str = ''.join(synonym)
                destination_synonym_str = synonym_str.split("=>")[1].strip()
                source_synonym_str_list = [element.strip() for element in synonym_str.split("=>")[0].split(",")]
                response.data[i].synonymKeyValue.append({destination_synonym_str: source_synonym_str_list})
        return response
    except Exception as e:
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e))
        return error_response
    
# Endpoint to create synonym map    
@app.post("/create-synonym-map")
def create_synonym_map(synonymData: SynonymData):
    global search_index_client
    synonymMapList = []
    try:
        # Check if synonym map already exists
        index = search_index_client.get_index(synonymData.indexName)
        # Construct synonym map strings
        for i, synonymMapKeyValue in enumerate(synonymData.synonymKeyValue):
            for key, value in synonymMapKeyValue.items():
                source_synonym = ", ".join(value)
                destination_synonym = key
                synonymMapList.append(f"{source_synonym} => {destination_synonym}")
        # Create synonym map
        search_index_client.create_synonym_map(SynonymMap(name=synonymData.mapName, synonyms=synonymMapList))
        logging.info(f"Synonym map {synonymData.mapName} created successfully")
        # Flag to indicate if the index was updated
        ifIndexChanged = False
        # Iterate through index fields to add the synonym map name
        for i, field in enumerate(index.fields):
            if index.fields[i].name == os.getenv("AZURE_SEARCH_INDEX_FIELD_NAME"):
                # Add the synonym map name if it does not exist in the field
                if synonymData.mapName not in index.fields[i].synonym_map_names:
                    index.fields[i].synonym_map_names.append(synonymData.mapName)
                    ifIndexChanged = True

        # Update the index if any changes were made
        if ifIndexChanged:
            search_index_client.create_or_update_index(index)
            logging.info(f"Synonym map {synonymData.mapName} added to {synonymData.indexName} index")
            return ResponseModel(code=200, message=status_codes.get(200))
        else:
            logging.info(f"Synonym map {synonymData.mapName} already exists in {synonymData.indexName} index")
            return ResponseModel(code=200, message=f"Synonym map {synonymData.mapName} already exists in {synonymData.indexName} index")
    except Exception as e:
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e), data=[])
        return error_response
    
# Endpoint to delete synonym map 
@app.delete("/delete-synonym-map")
def delete_synonym_map(deleteSynonymData:DeleteSynonymData):
    global search_index_client
    try:
        # Delete the synonym map
        search_index_client.delete_synonym_map(deleteSynonymData.mapName)
        # Get the index
        index = search_index_client.get_index(deleteSynonymData.indexName)
        # Flag to indicate if the index was updated
        ifIndexChanged = False
        # Iterate through index fields to remove the synonym map name
        for i, field in enumerate(index.fields):
            if index.fields[i].synonym_map_names is not None and len(field.synonym_map_names) > 0 and index.fields[i].name in [os.getenv("AZURE_SEARCH_INDEX_FIELD_NAME")]:
                    # Remove the synonym map name if it exists in the field
                    if deleteSynonymData.mapName in index.fields[i].synonym_map_names:
                        index.fields[i].synonym_map_names.remove(deleteSynonymData.mapName)
                        logging.info(f"Synonym map {deleteSynonymData.mapName} removed from {deleteSynonymData.indexName} index")
                        ifIndexChanged = True
        # Update the index if any changes were made
        if ifIndexChanged:
            search_index_client.create_or_update_index(index)
            logging.info(f"Synonym map {deleteSynonymData.mapName} removed from {deleteSynonymData.indexName} index")
            return ResponseModel(code=200, message=status_codes.get(200))
        else:
            logging.info(f"Synonym map not found in {deleteSynonymData.indexName} index")
            return ResponseModel(code=200, message=f"Synonym map not found in {deleteSynonymData.indexName} index")
    except Exception as e:
        # Handle exceptions and return error response
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e))
        return error_response



    
# Function to initialize Azure Search Index Client
def initialize_search_client():
    global search_index_client
    service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    search_index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(key))

# Load environment variables and initialize client
load_dotenv()
initialize_search_client()

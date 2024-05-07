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
# console_handler = logging.StreamHandler()
# Set the level of the console handler to INFO
# console_handler.setLevel(logging.INFO)
# Set the foramt
# console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# Add the console handler to the logger
# logging.getLogger().addHandler(console_handler)

# Load environment variables and initialize client
load_dotenv()

# Function to initialize Azure Search Index Client
service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
search_index_client = SearchIndexClient(service_endpoint, AzureKeyCredential(key))

app = FastAPI()

class SynonymData(BaseModel):
    indexName: str
    mapName: constr(min_length=1 , max_length=10)
    # Convert explicit mapping to equivalency mapping
    synonymList: List[List[str]] = []

    @field_validator("indexName")
    # check if indexName exists in Azure AI Search
    def check_indexName(cls, v):
        try:
            search_index_client.get_index(v)
        except Exception as e:
            logging.error(str(e))
            raise ValueError("IndexName does not exist in Azure AI Search")
        return v

    @field_validator("mapName")
    def check_mapName(cls, v):
        if v != v.lower():
            logging.error("MapName should be in Lowercase")
            raise ValueError("MapName should be in Lowercase")
        return v

    @field_validator("synonymList")
    def check_synonym_list(cls, v):
        # check if SynonymList is not empty
        if not v or len(v) < 1:
            logging.error("SynonymList cannot be empty")
            raise ValueError("SynonymList cannot be empty")
        for subSynonymList in v:
            # cehck if subSynonymList is not empty and whose length is greater than 1
            if not isinstance(subSynonymList,list) or not subSynonymList or not len(subSynonymList) > 1:
                logging.error("SubSynonymList should contain at least two non-empty elements")
                raise ValueError("SubSynonymList should contain at least two non-empty elements")
            else:
                # check if elements of the List are non-empty string
                for element in subSynonymList:
                    if not isinstance(element, str) or not element:
                        logging.error("SubSynonymList's elements should be non-empty string")
                        raise ValueError("SubSynonymList's elements should be non-empty string")
        return v
    
    

class ReadSynonymData(BaseModel):
    mapName: constr(min_length=1 , max_length=10)
    synonymList: List[List[str]] = []

class UpdatedSynonymData(BaseModel):
    indexName: str
    mapName: constr(min_length=1 , max_length=10)
    synonymList: List[List[str]] = []

    @field_validator("indexName")
    # check if indexName exists in Azure AI Search
    def check_indexName(cls, v):
        try:
            search_index_client.get_index(v)
        except Exception as e:
            logging.error(str(e))
            raise ValueError("IndexName does not exist in Azure AI Search")
        return v

    @field_validator("mapName")
    def check_mapName(cls, v):
        if v != v.lower():
            logging.error("MapName should be in Lowercase")
            raise ValueError("MapName should be in Lowercase")
        try:
            search_index_client.get_synonym_map(v)
        except Exception as e:
            logging.error(str(e))
            raise ValueError("MapName does not exist in Azure AI Search")
        return v

    @field_validator("synonymList")
    def check_synonym_list(cls, v):
        # check if SynonymList is not empty
        if not v or len(v) < 1:
            logging.error("SynonymList cannot be empty")
            raise ValueError("SynonymList cannot be empty")
        for subSynonymList in v:
            # cehck if subSynonymList is not empty and whose length is greater than 1
            if not isinstance(subSynonymList,list) or not subSynonymList or not len(subSynonymList) > 1:
                logging.error("SubSynonymList should contain at least two non-empty elements")
                raise ValueError("SubSynonymList should contain at least two non-empty elements")
            else:
                # check if elements of the List are non-empty string
                for element in subSynonymList:
                    if not isinstance(element, str) or not element:
                        logging.error("SubSynonymList's elements should be non-empty string")
                        raise ValueError("SubSynonymList's elements should be non-empty string")
        return v

class ReadSynonymDataByIndexName(BaseModel):
    indexName: str
    @field_validator("indexName")
    # check if indexName exists in Azure AI Search
    def check_indexName(cls, v):
        try:
            search_index_client.get_index(v)
        except Exception as e:
            logging.error(str(e))
            raise ValueError("IndexName does not exist in Azure AI Search")
        return v

class DeleteSynonymData(BaseModel):
    indexName: str
    mapName: constr(min_length=1 , max_length=10)

    @field_validator("indexName")
    # check if indexName exists in Azure AI Search
    def check_indexName(cls, v):
        try:
            search_index_client.get_index(v)
        except Exception as e:
            logging.error(str(e))
            raise ValueError("IndexName does not exist in Azure AI Search")
        return v

    @field_validator("mapName")
    def check_mapName(cls, v):
        if v != v.lower():
            logging.error("MapName should be in Lowercase")
            raise ValueError("MapName should be in Lowercase")
        return v

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
        search_index_client
        # Retrieve all synonym maps
        synonymMapNameList = search_index_client.get_synonym_maps()
        # Extract names of synonym maps
        names = [synonymMapName.name for synonymMapName in synonymMapNameList]
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
            # Test Convert explicit mapping to equivalency mapping
            # for j, synonym_format_str in enumerate(synonymMap.synonyms):
            #     # Extract destination synonym word and source synonym word list
            #     destination_synonym_str = synonym_format_str.split("=>")[1].strip()
            #     source_synonym_str_list = [element.strip() for element in synonym_format_str.split("=>")[0].split(",")]
            #     # Add synonym mapping to response data
            #     response.data[i].synonymKeyValue.append({destination_synonym_str: source_synonym_str_list})
            for j, synonym_format_str in enumerate(synonymMap.synonyms):
                # Extract destination synonym word and source synonym word list
                source_synonym_str_list = [element.strip() for element in synonym_format_str.split(",")]
                # Add synonym mapping to response data
                response.data[i].synonymList.append(source_synonym_str_list)
        return response
    except Exception as e:
        # Handle exceptions and return error response
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e))
        return error_response
    
# Endpoint of get synonym map by Azure search index name
@app.post("/get-synonymmap-by-aisearchindexname")
# def get_synonymmap_by_aisearchindexname(indexName: str):
def get_synonymmap_by_aisearchindexname(readSynonymDataByIndexName: ReadSynonymDataByIndexName):
    try:
        # Initialize Azure Search Index Client
        index = search_index_client.get_index(readSynonymDataByIndexName.indexName)
        synonymMapNameList = []
        synonymNameMappingList = []

        # retrieve synonym maps associated with the index
        for i, field in enumerate(index.fields):
            if field.synonym_map_names is not None and len(field.synonym_map_names) > 0:
                for synonymMapName in field.synonym_map_names:
                    synonymMapNameList.append(synonymMapName)
        # Remove duplicates from the list of synonym map names
        # temp_list = list(set(temp_list))
        synonymMapNameList = list(OrderedDict.fromkeys(synonymMapNameList))

        # If synonym maps exists, retrieve their details
        if(len(synonymMapNameList)>0):
            for i, name in enumerate(synonymMapNameList):
                synonymNameMappingList.append(search_index_client.get_synonym_map(name))

        # Create response model and populate with synonym map details
        response = ResponseModel(code=200, message=status_codes.get(200))
        # for i, synonymNameMapping in enumerate(synonymNameMappingList):
        #     response.data.append(SynonymData(indexName=indexName, mapName=synonymNameMapping.name, data=[]))
        #     for synonym in synonymNameMapping.synonyms:
        #         synonym_str = ''.join(synonym)
        #         destination_synonym_str = synonym_str.split("=>")[1].strip()
        #         source_synonym_str_list = [element.strip() for element in synonym_str.split("=>")[0].split(",")]
        #         response.data[i].synonymKeyValue.append({destination_synonym_str: source_synonym_str_list})
        for i, synonymNameMapping in enumerate(synonymNameMappingList):
            response.data.append(SynonymData(indexName=readSynonymDataByIndexName.indexName, mapName=synonymNameMapping.name, data=[]))
            for synonym in synonymNameMapping.synonyms:
                source_synonym_str_list = [element.strip() for element in synonym.split(",")]
                response.data[i].synonymList.append(source_synonym_str_list)
        return response
    except Exception as e:
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e))
        return error_response
    
# Endpoint to create synonym map    
@app.post("/create-synonym-map")
def create_synonym_map(synonymData: SynonymData):
    synonymEquivalencyRules = []
    try:
        # Check if synonym map already exists
        index = search_index_client.get_index(synonymData.indexName)
        # Construct synonym map strings
        # for i, synonymMapKeyValue in enumerate(synonymData.synonymKeyValue):
        #     for key, value in synonymMapKeyValue.items():
        #         source_synonym = ", ".join(value)
        #         destination_synonym = key
        #         synonymMapList.append(f"{source_synonym} => {destination_synonym}")
        for i, synonymOneList in enumerate(synonymData.synonymList):
            synonymEquivalencyStr = ", ".join(synonymOneList)
            synonymEquivalencyRules.append(synonymEquivalencyStr)

        # Create synonym map
        search_index_client.create_synonym_map(SynonymMap(name=synonymData.mapName, synonyms=synonymEquivalencyRules))
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
    search_index_client
    try:
        # Get the index
        index = search_index_client.get_index(deleteSynonymData.indexName)
        # Delete the synonym map
        search_index_client.delete_synonym_map(deleteSynonymData.mapName)
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

# Endpoint to update synonym map
@app.put("/update-synonym-map")
def update_synonym_map(updatedSynonymData: UpdatedSynonymData):
    synonymEquivalencyRules = []
    try:
        index = search_index_client.get_index(updatedSynonymData.indexName)
        for i, synonymOneList in enumerate(updatedSynonymData.synonymList):
            synonymEquivalencyStr = ", ".join(synonymOneList)
            synonymEquivalencyRules.append(synonymEquivalencyStr)

        search_index_client.create_or_update_synonym_map(SynonymMap(name=updatedSynonymData.mapName, synonyms=synonymEquivalencyRules))
        logging.info(f"Synonym map {updatedSynonymData.mapName} updated successfully")
        return ResponseModel(code=200, message=status_codes.get(200))
    except Exception as e:
        logging.error(str(e))
        error_response = ResponseModel(code=500, message=str(e), data=[])
        return error_response
    
        
        




    


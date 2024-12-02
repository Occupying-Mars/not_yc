import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, UpdateStatus
from typing import List
import json
from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def get_embedding(text, engine):
    response = client.embeddings.create(
        input=text,
        model=engine
    )
    embedding = response.data[0].embedding
    return embedding

class QdrantVectorStore:
    def __init__(self,
                 host: str = "localhost",
                 port: int = 6333,
                 db_path: str = "qdrant_storage",
                 collection_name: str = "transcripts_collection",
                 vector_size: int = 1536,
                 vector_distance=Distance.COSINE):
        self.client = QdrantClient(
            url=host,
            port=port,
        )
        self.collection_name = collection_name
        try:
            collection_info = self.client.get_collection(collection_name=collection_name)
            print(f"Collection '{collection_name}' already exists.")
        except Exception as e:
            print(f"Collection '{collection_name}' does not exist. Creating collection now.")
            self.set_up_collection(collection_name, vector_size, vector_distance)

    def set_up_collection(self, collection_name: str, vector_size: int, vector_distance: str):
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=vector_distance)
        )
        print(f"Collection '{collection_name}' created with vector size {vector_size} and distance {vector_distance}.")

    def upsert_data(self, data: List[dict], filename):
            points = []
            for item in data:
                content = item.get("content")
                start = item.get("start")
                end = item.get("end")
                url = item.get("url")
                title = item.get("title")
                text_vector = get_embedding(content, engine="text-embedding-3-small")
                text_id = str(uuid.uuid4())
                payload = {"content": content, "start": start, "end": end, "url": url, "title": title}
                point = PointStruct(id=text_id, vector=text_vector, payload=payload)
                points.append(point)
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            if operation_info.status == UpdateStatus.COMPLETED:
                print(f"Data from file '{filename}' has been uploaded successfully.")
            else:
                print("Failed to insert data")
    def search(self, input_query: str, limit: int = 3):
        input_vector = get_embedding(input_query, engine="text-embedding-3-small")
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=input_vector,
            limit=limit
        )
        result = []
        for item in search_result:
            similarity_score = item.score
            payload = item.payload
            data = {
                "id": item.id,
                "similarity_score": similarity_score,
                "start": payload.get("start"),
                "end": payload.get("end"),
                "content": payload.get("content"),
                "url": payload.get("url"),
                "title": payload.get("title")
            }
            result.append(data)
        print(json.dumps(result, indent=4))
        return result
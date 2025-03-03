import pinecone
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone.init(
    api_key=os.getenv("PINECONE_API_KEY"),
    environment=os.getenv("PINECONE_ENV")
)
index = pinecone.Index(os.getenv("PINECONE_INDEX"))

def ingest_documents():
    # Sample documents - replace with your own data
    documents = [
        "RAG (Retrieval-Augmented Generation) enhances language models by incorporating external knowledge",
        "Vector databases store embeddings for efficient similarity search",
        "OpenAI's GPT-4 is a state-of-the-art language model",
        "Pinecone is a managed vector database service",
        "GitHub Codespaces provides cloud-based development environments"
    ]

    # Process and store documents
    for i, text in enumerate(documents):
        # Generate embedding
        embedding = openai_client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        ).data[0].embedding

        # Upsert to Pinecone
        index.upsert(
            vectors=[{
                "id": f"doc_{i}",
                "values": embedding,
                "metadata": {"text": text}
            }]
        )
        print(f"Inserted document {i}")

    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_documents()

# create_index.py
import pinecone

pc = pinecone.Pinecone(api_key="pcsk_3gR846_RefFWHrEhBgeRxEixtMkFvJ1Y28NQL5bkGvT1H8X2cnDPdsDswNyvfY7AXrQMUN")

index_name = "rag-chatbot"

# Delete existing index if wrong dimension
if index_name in pc.list_indexes().names():
    pc.delete_index(index_name)

# Create new index with correct dimension
pc.create_index(
    name=index_name,
    dimension=1536,  # Must match OpenAI embedding size
    metric="cosine",
    spec=pinecone.ServerlessSpec(
        cloud="aws",  # or "gcp"/"azure"
        region="us-east-1"  # Match your PINECONE_ENV
    )
)
print("Index created with dimension 1536")
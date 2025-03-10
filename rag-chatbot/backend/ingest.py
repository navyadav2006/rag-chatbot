import os
import sys
import psycopg2  # PostgreSQL connector for Python
from pinecone import Pinecone
from openai import OpenAI

# Debug: Start of the script
print("Starting ingestion process...")
sys.stdout.flush()

# Initialize OpenAI and Pinecone connections
try:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENV"))
    index = pc.Index("openai-embeddings")
    print("OpenAI and Pinecone clients initialized.")
except Exception as e:
    print(f"Error initializing clients: {e}")
    sys.exit(1)

# Connect to PostgreSQL (Supabase or your PostgreSQL provider)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL is not set. Please set it in your environment variables.")
    sys.exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("Connected to the database.")
except Exception as e:
    print(f"Error connecting to the database: {e}")
    sys.exit(1)

# Query the Products table for car parts details
try:
    cursor.execute("SELECT product_name, description, brand, unit_price, stock_level FROM products")
    rows = cursor.fetchall()
    print(f"Fetched {len(rows)} rows from the database.")
except Exception as e:
    print(f"Error executing query: {e}")
    conn.close()
    sys.exit(1)

# Process each row into a document and upsert into Pinecone
for i, row in enumerate(rows):
    product_name, description, brand, unit_price, stock_level = row
    doc_text = (
        f"Product: {product_name}\n"
        f"Description: {description}\n"
        f"Brand: {brand}\n"
        f"Unit Price: ${unit_price}\n"
        f"Stock Level: {stock_level}"
    )
    
    try:
        # Generate an embedding for the document text
        embedding_response = openai_client.embeddings.create(
            input=doc_text,
            model="text-embedding-ada-002"
        )
        embedding = embedding_response.data[0].embedding

        # Upsert the vector into Pinecone with metadata
        index.upsert(vectors=[{
            "id": f"prod_{i}",
            "values": embedding,
            "metadata": {
                "product_name": product_name,
                "description": description,
                "brand": brand,
                "unit_price": unit_price,
                "stock_level": stock_level,
                "text": doc_text
            }
        }])
        
        print(f"Inserted: {doc_text[:50]}...")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error processing row {i}: {e}")

# Close database connection
conn.close()
print("Data ingestion complete!")
sys.stdout.flush()

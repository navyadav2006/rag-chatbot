import sys
import psycopg2  # PostgreSQL connector for Python
from pinecone import Pinecone
from pinecone import ServerlessSpec
from openai import OpenAI

# Debug: Start of the script
print("🔍 Starting ingestion process...")
sys.stdout.flush()

# Hardcoded Supabase Credentials
DATABASE_URL = "postgresql://postgres.wsyldoevqmzwjhpeoghs:Navnia0211@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

# OpenAI & Pinecone API Keys
OPENAI_API_KEY = "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"
PINECONE_API_KEY = "pcsk_3gR846_RefFWHrEhBgeRxEixtMkFvJ1Y28NQL5bkGvT1H8X2cnDPdsDswNyvfY7AXrQMUN"
PINECONE_INDEX_NAME = "rag-chatbot"

# Initialize OpenAI and Pinecone clients
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    print("✅ OpenAI and Pinecone clients initialized.")
except Exception as e:
    print(f"❌ Error initializing clients: {e}")
    sys.exit(1)

# Check if Pinecone Index Exists, If Not, Create It
existing_indexes = pinecone_client.list_indexes().names()
if PINECONE_INDEX_NAME not in existing_indexes:
    print(f"⚠️ Index '{PINECONE_INDEX_NAME}' not found. Creating it...")
    pinecone_client.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(  # ✅ Correctly specifying serverless spec
                cloud="aws",
                region="us-east-1"
            )
    )
    print(f"✅ Index '{PINECONE_INDEX_NAME}' created.")

# Connect to Pinecone Index
index = pinecone_client.Index(PINECONE_INDEX_NAME)
print(f"✅ Connected to Pinecone index '{PINECONE_INDEX_NAME}'.")

# Connect to Supabase PostgreSQL
try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Connected to Supabase database.")
except Exception as e:
    print(f"❌ Error connecting to the database: {e}")
    sys.exit(1)

# Query the Products table for full product details
try:
    cursor.execute("SELECT id, product_name, description, brand, unit_price, stock_level FROM products")
    rows = cursor.fetchall()
    print(f"📦 Fetched {len(rows)} products from the database.")
except Exception as e:
    print(f"❌ Error executing query: {e}")
    conn.close()
    sys.exit(1)

# Process each row into a document and upsert into Pinecone
for i, row in enumerate(rows):
    product_id, product_name, description, brand, unit_price, stock_level = row
    doc_text = (
        f"Product Name: {product_name}\n"
        f"Description: {description}\n"
        f"Brand: {brand}\n"
        f"Unit Price: ${unit_price}\n"
        f"Stock Level: {stock_level}"
    )
    
    try:
        # Generate embedding for the document text
        embedding_response = openai_client.embeddings.create(
            input=doc_text,
            model="text-embedding-ada-002"
        )
        embedding = embedding_response.data[0].embedding

        # Upsert vector into Pinecone with full metadata
        index.upsert(vectors=[{
            "id": f"product_{product_id}",
            "values": embedding,
            "metadata": {
                "product_id": product_id,
                "product_name": product_name,
                "description": description,
                "brand": brand,
                "unit_price": unit_price,
                "stock_level": stock_level
            }
        }])
        
        print(f"✅ Inserted: {product_name} (ID: {product_id}) into Pinecone.")
        sys.stdout.flush()
    except Exception as e:
        print(f"❌ Error processing product {product_name}: {e}")

# Close database connection
conn.close()
print("✅ Data ingestion complete!")
sys.stdout.flush()

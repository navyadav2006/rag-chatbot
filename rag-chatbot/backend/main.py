from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone
from openai import OpenAI
import os
import signal
import sys
from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

@app.get("/test-supabase")
async def test_connection():
    try:
        # Test connection
        result = supabase.table('products').select("*").limit(1).execute()
        return {"status": "connected", "data": result.data}
    except Exception as e:
        return {"error": str(e)}
def handle_exit(signum, frame):
    print("\nGracefully shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Handle termination signals
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Disable auto-reload in production
        workers=1      # Use single worker for Codespaces
    )

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "RAG Chatbot API is running"}

# Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    #allow_origins=["http://localhost:8000", "https://*.githubpreview.dev"],
    #allow_origins=["*"],
    allow_origins=[
        "https://zany-garbanzo-69wgvr4696rr2q59-8000.app.github.dev",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI services
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(
    api_key=os.getenv("PINECONE_API_KEY")
)

# Connect to your index
index = pc.Index(os.getenv("PINECONE_INDEX"))

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask(request: QuestionRequest):
    print(f"Received question: {request.question}")
    # Create embedding
    embedding = openai_client.embeddings.create(
        input=request.question,
        model="text-embedding-ada-002"
    ).data[0].embedding

    # Search Pinecone
    results = index.query(
        vector=embedding,
        top_k=3,
        include_metadata=True
    )
    context = [match.metadata["text"] for match in results.matches]

    # Generate response
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"Answer using: {context}"},
            {"role": "user", "content": request.question}
        ]
    )
    print(f"OpenAI response: {response.choices[0].message.content}")  # Verify this
    return {"answer": response.choices[0].message.content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
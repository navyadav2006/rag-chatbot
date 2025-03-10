import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
from openai import OpenAI
from pinecone import Pinecone
from starlette.responses import JSONResponse

# ✅ Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔹 Hardcoded API Keys (Security Risk for Production)
SUPABASE_URL = "https://wsyldoevqmzwjhpeoghs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndzeWxkb2V2cW16d2pocGVvZ2hzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExODU4NDQsImV4cCI6MjA1Njc2MTg0NH0.4k6AtYDzgm8R4AFAMXxSecqlo4jR8rVh44-jPmPFheo"
OPENAI_API_KEY = "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"
PINECONE_API_KEY = "pcsk_3gR846_RefFWHrEhBgeRxEixtMkFvJ1Y28NQL5bkGvT1H8X2cnDPdsDswNyvfY7AXrQMUN"
PINECONE_INDEX_NAME = "rag-chatbot"

# ✅ Initialize FastAPI App
app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zany-garbanzo-69wgvr4696rr2q59-8000.app.github.dev",
        "https://zany-garbanzo-69wgvr4696rr2q59-8001.app.github.dev",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ✅ Handle Preflight Requests
@app.options("/{full_path:path}")
async def preflight_request(full_path: str):
    response = JSONResponse({"message": "Preflight request successful."})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# ✅ CORS Middleware
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# ✅ Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Initialize OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Initialize Pinecone
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
index = pinecone_client.Index(PINECONE_INDEX_NAME)

# ---------------------------------------------------------------
# ✅ **User Authentication Models**
# ---------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ---------------------------------------------------------------
# ✅ **User Registration**
# ---------------------------------------------------------------
@app.post("/register")
async def register_user(user: RegisterRequest):
    try:
        # Check if email already exists
        existing_user = supabase.table("users").select("email").eq("email", user.email).execute()
        if existing_user.data:
            raise HTTPException(status_code=400, detail="User already exists")

        # Insert new user into Supabase
        response = supabase.table("users").insert({
            "username": user.username,
            "email": user.email,
            "password": user.password
        }).execute()

        return {"message": "User registered successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------
# ✅ **User Login**
# ---------------------------------------------------------------
@app.post("/login")
async def login(user: LoginRequest):
    try:
        # Fetch user details by email
        response = supabase.table("users").select("*").eq("email", user.email).execute()
        user_data = response.data
        
        if not user_data:
            raise HTTPException(status_code=400, detail="User not found")

        user_record = user_data[0]  # Get user details
        
        # Compare provided password with stored password
        if user.password != user_record["password"]:
            raise HTTPException(status_code=400, detail="Invalid credentials")

        return {"message": "Login successful", "user": {"email": user_record["email"], "username": user_record["username"]}}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------
# ✅ **Question Request Model**
# ---------------------------------------------------------------
class QuestionRequest(BaseModel):
    question: str

# ---------------------------------------------------------------
# ✅ **AI Chatbot Endpoint - Uses Pinecone & OpenAI**
# ---------------------------------------------------------------
@app.post("/ask")
async def ask_question(request: QuestionRequest):
    try:
        logger.info(f"Processing question: {request.question}")

        # 🔹 Generate embedding
        embedding = openai_client.embeddings.create(
            input=request.question,
            model="text-embedding-ada-002"
        ).data[0].embedding

        # 🔹 Query Pinecone
        results = index.query(
            vector=embedding,
            top_k=5,
            include_metadata=True
        )

        # 🔹 Extract relevant product data
        context = "\n".join([
            f"{r.metadata['product_name']} ({r.metadata['brand']}): {r.metadata['description']}, Price: ${r.metadata['unit_price']}, Stock: {r.metadata['stock_level']}"
            for r in results.matches
        ])

        # 🔹 Generate AI response using OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": f"Provide product details using:\n{context}"
            }, {
                "role": "user",
                "content": request.question
            }]
        )

        return {"answer": response.choices[0].message.content}

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(500, detail="Service error")

# ---------------------------------------------------------------
# ✅ **Health Check Endpoint**
# ---------------------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import activity
import logging
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Activity Generator API", version="1.0.0")

# CORS middleware to allow all origins - MUST be added FIRST (before other middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"→ {request.method} {request.url}")
    logger.info(f"  Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"← {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

# Include routers
app.include_router(activity.router, prefix="/api", tags=["activity"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested - server is running")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


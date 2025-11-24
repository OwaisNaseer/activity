from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from routers import activity
import logging
from dotenv import load_dotenv
import time
import traceback

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Activity Generator API", version="1.0.0")

# Global exception handler to catch all unhandled exceptions (except HTTPException and RequestValidationError)
# This must be registered BEFORE other exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return proper error response"""
    # Don't handle HTTPException or RequestValidationError - let FastAPI handle them
    if isinstance(exc, (HTTPException, RequestValidationError)):
        raise exc
    
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # For /api/generate-activity endpoint, return ActivityResponse format
    if "/api/generate-activity" in str(request.url):
        return JSONResponse(
            status_code=200,  # Return 200 so frontend can read the error
            content={
                "success": False,
                "activity": None,
                "error": f"Server error: {str(exc)}"
            }
        )
    else:
        # For other endpoints, return standard error
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(exc)}"}
        )

# Handle validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation error: {str(exc)}")
    # For /api/generate-activity endpoint, return ActivityResponse format
    if "/api/generate-activity" in str(request.url):
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "activity": None,
                "error": f"Validation error: {str(exc)}"
            }
        )
    else:
        # For other endpoints, return standard validation error
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)}
        )

# CORS middleware to allow all origins - MUST be added FIRST (before other middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
)

# Add request logging middleware with error catching
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"→ {request.method} {request.url}")
    logger.info(f"  Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"← {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.3f}s")
        return response
    except Exception as e:
        # Catch any unhandled exceptions in middleware
        logger.error(f"Middleware error: {str(e)}", exc_info=True)
        process_time = time.time() - start_time
        logger.error(f"← {request.method} {request.url} - ERROR - Time: {process_time:.3f}s")
        
        # For /api/generate-activity, return ActivityResponse format
        if "/api/generate-activity" in str(request.url):
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "activity": None,
                    "error": f"Middleware error: {str(e)}"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(e)}"}
            )

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


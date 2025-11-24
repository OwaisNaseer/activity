from fastapi import APIRouter, HTTPException
import logging
from models.activity import ActivityRequest, ActivityResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy import and initialization of generator to avoid import errors at module load time
_generator = None
_generator_error = None

def get_generator(force_reload=False):
    """Lazy load the generator to avoid import errors at module load time
    
    Args:
        force_reload: If True, reload environment variables and reinitialize generator
    """
    global _generator, _generator_error
    
    # Force reload if requested (useful when .env changes)
    if force_reload:
        logger.info("Forcing generator reload...")
        _generator = None
        _generator_error = None
        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)
    
    if _generator is not None:
        return _generator
    
    if _generator_error is not None and not force_reload:
        return None
    
    try:
        from services.generator import ActivityGenerator
        _generator = ActivityGenerator()
        logger.info("ActivityGenerator initialized successfully")
        # Check if API key is configured
        if hasattr(_generator, 'api_key') and _generator.api_key:
            logger.info(f"OpenAI API key is configured (prefix: {_generator.api_key[:10]}...)")
        else:
            logger.warning("OpenAI API key is NOT configured - will use template responses")
        return _generator
    except ImportError as e:
        _generator_error = f"Failed to import generator: {str(e)}"
        logger.error(_generator_error, exc_info=True)
        return None
    except Exception as e:
        _generator_error = f"Failed to initialize ActivityGenerator: {str(e)}"
        logger.error(_generator_error, exc_info=True)
        return None

@router.post("/generate-activity", response_model=ActivityResponse)
async def generate_activity(request: ActivityRequest):
    """
    Generate a professional activity description based on input parameters
    """
    try:
        # Get generator (lazy load) - try to reload if no API key
        generator = get_generator()
        
        # If generator exists but has no API key, try to reload
        if generator and (not hasattr(generator, 'api_key') or not generator.api_key):
            logger.info("Generator has no API key, attempting to reload...")
            generator = get_generator(force_reload=True)
        
        # Check if generator is available
        if generator is None:
            error_msg = _generator_error or "Generator service is not available. Please check server configuration."
            logger.error(f"ActivityGenerator is not available: {error_msg}")
            return ActivityResponse(
                success=False,
                activity=None,
                error=error_msg
            )
        
        # Log the request with full details
        logger.info("=" * 60)
        logger.info("ACTIVITY GENERATION REQUEST RECEIVED")
        logger.info(f"  Subject: {request.subject}")
        logger.info(f"  Grade/Band: {request.grade_band}")
        logger.info(f"  Topic/Concept: {request.topic_concept}")
        logger.info(f"  Available Time: {request.available_time} minutes")
        logger.info(f"  Output Language: {request.output_language}")
        logger.info(f"  Materials: {request.available_materials or 'Not specified'}")
        logger.info(f"  Constraints: {request.constraints or 'None specified'}")
        logger.info("=" * 60)
        
        # Validate input
        if not request.subject or not request.topic_concept:
            logger.warning("Validation failed: Subject or Topic/Concept missing")
            return ActivityResponse(
                success=False,
                activity=None,
                error="Subject and Topic/Concept are required"
            )
        
        if request.available_time <= 0:
            logger.warning("Validation failed: Invalid available_time")
            return ActivityResponse(
                success=False,
                activity=None,
                error="Available time must be greater than 0"
            )
        
        # Convert request to dict for the generator
        request_data = {
            "subject": request.subject,
            "grade_band": request.grade_band,
            "topic_concept": request.topic_concept,
            "available_materials": request.available_materials or "",
            "constraints": request.constraints or "",
            "available_time": request.available_time,
            "output_language": request.output_language
        }
        
        # Generate activity - FastAPI can handle sync functions in async endpoints
        try:
            logger.info("Calling generator.generate_activity...")
            logger.info(f"Generator state check - API Key configured: {hasattr(generator, 'api_key') and generator.api_key is not None}")
            logger.info(f"Generator state check - Client initialized: {hasattr(generator, 'client') and generator.client is not None}")
            
            success, activity, error = generator.generate_activity(request_data)
            
            logger.info(f"Generator returned: success={success}, activity_length={len(activity) if activity else 0}, error={error}")
            
            # If generation failed, log the error for debugging
            if not success and error:
                logger.error(f"Generation failed with error: {error}")
                # Include the error in the response so frontend can show it
                # But still return the template activity if available
                if activity:
                    logger.info("Template activity was generated, returning it with error message")
        except Exception as gen_error:
            logger.error(f"Exception during generation: {str(gen_error)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            success, activity, error = False, None, f"Generation error: {str(gen_error)}"
        
        # Return response - ensure all fields are properly set
        try:
            if success and activity:
                logger.info(f"Activity generated successfully ({len(activity)} characters)")
                # Ensure activity is a string and not None
                activity_str = str(activity) if activity else ""
                if not activity_str:
                    # If activity is empty, treat as failure
                    return ActivityResponse(
                        success=False,
                        activity=None,
                        error="Generated activity is empty"
                    )
                return ActivityResponse(
                    success=True,
                    activity=activity_str,
                    error=None
                )
            else:
                error_msg = str(error) if error else "Failed to generate activity"
                logger.error(f"Failed to generate activity: {error_msg}")
                
                # If we have a template activity but generation failed, return it with the error
                if activity:
                    logger.info("Returning template activity with error message for user awareness")
                    return ActivityResponse(
                        success=True,  # Still return success since we have content
                        activity=str(activity),
                        error=f"Note: {error_msg}"  # Include error as a note
                    )
                else:
                    return ActivityResponse(
                        success=False,
                        activity=None,
                        error=error_msg
                    )
        except Exception as resp_error:
            logger.error(f"Error creating response: {str(resp_error)}", exc_info=True)
            # Last resort - return a basic response
            return ActivityResponse(
                success=False,
                activity=None,
                error=f"Response creation error: {str(resp_error)}"
            )
            
    except HTTPException as he:
        # Re-raise HTTP exceptions (like 400 Bad Request) - but wrap in ActivityResponse for this endpoint
        logger.warning(f"HTTPException raised: {he.detail}")
        return ActivityResponse(
            success=False,
            activity=None,
            error=he.detail
        )
    except Exception as e:
        logger.error(f"Unexpected error in generate_activity endpoint: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Always return ActivityResponse, never raise 500
        try:
            return ActivityResponse(
                success=False,
                activity=None,
                error=f"Internal server error: {str(e)}"
            )
        except Exception as final_error:
            # If even ActivityResponse fails, return dict (shouldn't happen)
            logger.critical(f"CRITICAL: Cannot create ActivityResponse: {str(final_error)}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "activity": None,
                    "error": f"Critical error: {str(e)}"
                }
            )


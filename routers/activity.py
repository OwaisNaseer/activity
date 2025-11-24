from fastapi import APIRouter, HTTPException
import logging
from models.activity import ActivityRequest, ActivityResponse
from services.generator import ActivityGenerator

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize the generator service
generator = ActivityGenerator()

@router.post("/generate-activity", response_model=ActivityResponse)
async def generate_activity(request: ActivityRequest):
    """
    Generate a professional activity description based on input parameters
    """
    try:
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
            raise HTTPException(status_code=400, detail="Subject and Topic/Concept are required")
        
        if request.available_time <= 0:
            raise HTTPException(status_code=400, detail="Available time must be greater than 0")
        
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
        
        # Generate activity
        success, activity, error = generator.generate_activity(request_data)
        
        if success and activity:
            logger.info("Activity generated successfully")
            return ActivityResponse(success=True, activity=activity, error=None)
        else:
            logger.error(f"Failed to generate activity: {error}")
            return ActivityResponse(success=False, activity=None, error=error or "Failed to generate activity")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


from pydantic import BaseModel, Field
from typing import Optional

class ActivityRequest(BaseModel):
    """Request model for activity generation"""
    subject: str = Field(..., description="Subject name")
    grade_band: str = Field(..., description="Grade or band level")
    topic_concept: str = Field(..., description="Topic or concept to teach")
    available_materials: Optional[str] = Field(None, description="Available materials for the activity")
    constraints: Optional[str] = Field(None, description="Constraints or limitations")
    available_time: int = Field(..., description="Available time in minutes", gt=0)
    output_language: str = Field(..., description="Output language for the activity")

class ActivityResponse(BaseModel):
    """Response model for generated activity"""
    success: bool
    activity: Optional[str] = None
    error: Optional[str] = None


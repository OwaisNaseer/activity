from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ActivityRequest(BaseModel):
    """Request model for activity generation"""
    subject: str = Field(..., description="Subject name")
    grade_band: str = Field(..., description="Grade or band level")
    topic_concept: str = Field(..., description="Topic or concept to teach")
    available_materials: Optional[str] = Field(None, description="Available materials for the activity")
    constraints: Optional[str] = Field(None, description="Constraints or limitations")
    available_time: int = Field(..., description="Available time in minutes", gt=0)
    output_language: str = Field(..., description="Output language for the activity")
    standard: Optional[str] = Field(None, description="Educational standard")
    regenerate: Optional[bool] = Field(False, description="Whether this is a regeneration request")
    language: Optional[str] = Field(None, description="Language for 'Other' option")
    num_variants: int = Field(1, description="Number of variants to generate (1-3)", ge=1, le=3)

class ActivityResponse(BaseModel):
    """Response model for generated activity"""
    success: bool
    activity: Optional[str] = None  # For backward compatibility (single variant)
    activities: Optional[List[str]] = None  # For multiple variants
    structured_activities: Optional[List[Dict[str, Any]]] = None  # TOON-based payload (plain dicts)
    error: Optional[str] = None


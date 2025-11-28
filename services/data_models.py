"""Data models for activity generation service.

This module contains all Pydantic models for request/response validation
and structured data handling following Pydantic V2 standards.
"""
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, constr, ValidationError


# ============================================================================
# Request Models
# ============================================================================

class ActivityRequest(BaseModel):
    """Request model for activity generation.
    
    Attributes:
        subject: Subject name (e.g., "Science", "Mathematics")
        grade_band: Grade or band level (e.g., "5th grade", "Year 7")
        topic_concept: Topic or concept to teach
        available_materials: Optional available materials for the activity
        constraints: Optional constraints or limitations
        available_time: Available time in minutes (must be > 0)
        output_language: Output language for the activity
        standard: Optional educational standard identifier
        regenerate: Whether this is a regeneration request
        language: Language for 'Other' option when output_language is "Other"
        num_variants: Number of variants to generate (1-3)
    """
    subject: str = Field(..., description="Subject name", min_length=1)
    grade_band: str = Field(..., description="Grade or band level", min_length=1)
    topic_concept: str = Field(..., description="Topic or concept to teach", min_length=1)
    available_materials: Optional[str] = Field(None, description="Available materials for the activity")
    constraints: Optional[str] = Field(None, description="Constraints or limitations")
    available_time: int = Field(..., description="Available time in minutes", gt=0)
    output_language: str = Field(..., description="Output language for the activity", min_length=1)
    standard: Optional[str] = Field(None, description="Educational standard identifier")
    regenerate: Optional[bool] = Field(False, description="Whether this is a regeneration request")
    language: Optional[str] = Field(None, description="Language for 'Other' option")
    num_variants: int = Field(1, description="Number of variants to generate (1-3)", ge=1, le=3)


# ============================================================================
# Lesson Plan Component Models
# ============================================================================

class LessonMeta(BaseModel):
    """Shared metadata describing the generated lesson.
    
    Attributes:
        subject: Subject name (e.g., "Science")
        grade_band: Grade or band level (e.g., "5th grade")
        topic: Target concept or topic
        available_time: Available time in minutes (must be > 0)
        language: Language used in the lesson output
        standard: Optional educational standard identifier
        constraints: Optional key constraints to honor
    """
    subject: str = Field(..., description="Subject name, e.g., Science", min_length=1)
    grade_band: str = Field(..., description="Grade or band level, e.g., 5th grade", min_length=1)
    topic: str = Field(..., description="Target concept or topic", min_length=1)
    available_time: int = Field(..., description="Available time in minutes", gt=0)
    language: str = Field(..., description="Language used in the lesson output", min_length=1)
    standard: Optional[str] = Field(None, description="Educational standard identifier")
    constraints: Optional[str] = Field(None, description="Key constraints to honor")


class LessonObjective(BaseModel):
    """Single instructional objective.
    
    Attributes:
        label: Objective label/identifier
        text: Objective description text
    """
    label: constr(strip_whitespace=True, min_length=1) = Field(..., description="Objective label")
    text: constr(strip_whitespace=True, min_length=1) = Field(..., description="Objective text")


class AssessmentCriterion(BaseModel):
    """Rubric or evaluation criterion.
    
    Attributes:
        focus: Focus area of the criterion
        detail: Detailed description of the criterion
    """
    focus: constr(strip_whitespace=True, min_length=1) = Field(..., description="Criterion focus area")
    detail: constr(strip_whitespace=True, min_length=1) = Field(..., description="Criterion detail")


class Assessment(BaseModel):
    """Assessment overview plus rubric criteria.
    
    Attributes:
        overview: Assessment overview description
        criteria: List of assessment criteria
    """
    overview: constr(strip_whitespace=True, min_length=1) = Field(..., description="Assessment overview")
    criteria: List[AssessmentCriterion] = Field(..., description="List of assessment criteria", min_length=1)


class LessonStep(BaseModel):
    """Atomic action inside a lesson section.
    
    Attributes:
        label: Step label/identifier
        duration: Step duration (e.g., "5 minutes")
        detail: Step detail description
    """
    label: constr(strip_whitespace=True, min_length=1) = Field(..., description="Step label")
    duration: constr(strip_whitespace=True, min_length=1) = Field(..., description="Step duration")
    detail: constr(strip_whitespace=True, min_length=1) = Field(..., description="Step detail")


class LessonSection(BaseModel):
    """Structured grouping for lesson phases.
    
    Attributes:
        id: Section identifier (e.g., "opening", "guided_practice")
        title: Section title
        goal: Section goal description
        steps: List of steps in this section
    """
    id: constr(strip_whitespace=True, min_length=2) = Field(..., description="Section identifier")
    title: constr(strip_whitespace=True, min_length=2) = Field(..., description="Section title")
    goal: constr(strip_whitespace=True, min_length=2) = Field(..., description="Section goal")
    steps: List[LessonStep] = Field(..., description="List of steps in this section", min_length=1)


class ExtensionTask(BaseModel):
    """Optional extension challenge.
    
    Attributes:
        title: Extension task title
        detail: Extension task detail description
    """
    title: constr(strip_whitespace=True, min_length=1) = Field(..., description="Extension task title")
    detail: constr(strip_whitespace=True, min_length=1) = Field(..., description="Extension task detail")


class HomeworkTask(BaseModel):
    """Homework expectations.
    
    Attributes:
        prompt: Homework prompt/instruction
        deliverable: Expected deliverable description
    """
    prompt: constr(strip_whitespace=True, min_length=1) = Field(..., description="Homework prompt")
    deliverable: constr(strip_whitespace=True, min_length=1) = Field(..., description="Expected deliverable")


# ============================================================================
# Lesson Plan Model
# ============================================================================

class LessonPlan(BaseModel):
    """Full TOON lesson definition.
    
    This is the main model representing a complete lesson plan with all
    required components. It follows the TOON schema specification.
    
    Attributes:
        schema_id: Schema identifier (always "toon.lesson.v1")
        meta: Lesson metadata
        title: Lesson title (minimum 3 characters)
        key_points: List of key points (typically 5 items)
        objectives: List of learning objectives
        assessment: Assessment details
        sections: List of lesson sections
        extension: Extension task
        homework: Homework task
        notes: List of notes
        materials: List of required materials
    """
    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    
    schema_id: Literal["toon.lesson.v1"] = Field(
        "toon.lesson.v1",
        alias="schema",
        description="TOON schema identifier"
    )
    meta: LessonMeta = Field(..., description="Lesson metadata")
    title: constr(strip_whitespace=True, min_length=3) = Field(..., description="Lesson title")
    key_points: List[constr(strip_whitespace=True, min_length=1)] = Field(
        ...,
        description="List of key points",
        min_length=1
    )
    objectives: List[LessonObjective] = Field(
        ...,
        description="List of learning objectives",
        min_length=1
    )
    assessment: Assessment = Field(..., description="Assessment details")
    sections: List[LessonSection] = Field(
        ...,
        description="List of lesson sections",
        min_length=1
    )
    extension: ExtensionTask = Field(..., description="Extension task")
    homework: HomeworkTask = Field(..., description="Homework task")
    notes: List[constr(strip_whitespace=True, min_length=1)] = Field(
        ...,
        description="List of notes",
        min_length=1
    )
    materials: List[constr(strip_whitespace=True, min_length=1)] = Field(
        ...,
        description="List of required materials",
        min_length=1
    )


# ============================================================================
# Bundle Model
# ============================================================================

class LessonBundle(BaseModel):
    """Wrapper for returning multiple lesson plan variants in a single payload.
    
    Attributes:
        schema_id: Schema identifier (always "toon.bundle.v1")
        variants: List of lesson plan variants
    """
    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    
    schema_id: Literal["toon.bundle.v1"] = Field(
        "toon.bundle.v1",
        alias="schema",
        description="TOON bundle schema identifier"
    )
    variants: List[LessonPlan] = Field(
        ...,
        description="List of lesson plan variants",
        min_length=1
    )


# ============================================================================
# Response Models
# ============================================================================

class ActivityResponse(BaseModel):
    """Response model for generated activity.
    
    Attributes:
        success: Whether the generation was successful
        activity: Single activity string (for backward compatibility, single variant)
        activities: List of activity strings (for multiple variants)
        structured_activities: List of structured lesson plan dicts (TOON-based payload)
        error: Optional error message if generation failed
    """
    success: bool = Field(..., description="Whether generation was successful")
    activity: Optional[str] = Field(None, description="Single activity string (backward compatibility)")
    activities: Optional[List[str]] = Field(None, description="List of activity strings (multiple variants)")
    structured_activities: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of structured lesson plan dicts (TOON-based payload)"
    )
    error: Optional[str] = Field(None, description="Error message if generation failed")


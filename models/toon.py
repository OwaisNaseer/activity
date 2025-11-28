"""Pydantic models for the TOON (Token-Oriented Object Notation) lesson schema."""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, constr


class LessonMeta(BaseModel):
    """Shared metadata describing the generated lesson."""

    subject: str = Field(..., description="Subject name, e.g., Science")
    grade_band: str = Field(..., description="Grade or band level, e.g., 5th grade")
    topic: str = Field(..., description="Target concept or topic")
    available_time: int = Field(..., description="Available time in minutes", gt=0)
    language: str = Field(..., description="Language used in the lesson output")
    standard: Optional[str] = Field(None, description="Educational standard identifier")
    constraints: Optional[str] = Field(None, description="Key constraints to honor")


class LessonObjective(BaseModel):
    """Single instructional objective."""

    label: constr(strip_whitespace=True, min_length=1)
    text: constr(strip_whitespace=True, min_length=1)


class AssessmentCriterion(BaseModel):
    """Rubric or evaluation criterion."""

    focus: constr(strip_whitespace=True, min_length=1)
    detail: constr(strip_whitespace=True, min_length=1)


class Assessment(BaseModel):
    """Assessment overview plus rubric criteria."""

    overview: constr(strip_whitespace=True, min_length=1)
    criteria: List[AssessmentCriterion]


class LessonStep(BaseModel):
    """Atomic action inside a section."""

    label: constr(strip_whitespace=True, min_length=1)
    duration: constr(strip_whitespace=True, min_length=1)
    detail: constr(strip_whitespace=True, min_length=1)


class LessonSection(BaseModel):
    """Structured grouping for lesson phases."""

    id: constr(strip_whitespace=True, min_length=2)
    title: constr(strip_whitespace=True, min_length=2)
    goal: constr(strip_whitespace=True, min_length=2)
    steps: List[LessonStep]


class ExtensionTask(BaseModel):
    """Optional extension challenge."""

    title: constr(strip_whitespace=True, min_length=1)
    detail: constr(strip_whitespace=True, min_length=1)


class HomeworkTask(BaseModel):
    """Homework expectations."""

    prompt: constr(strip_whitespace=True, min_length=1)
    deliverable: constr(strip_whitespace=True, min_length=1)


class LessonPlan(BaseModel):
    """Full TOON lesson definition."""

    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    schema_id: Literal["toon.lesson.v1"] = Field("toon.lesson.v1", alias="schema")
    meta: LessonMeta
    title: constr(strip_whitespace=True, min_length=3)
    key_points: List[constr(strip_whitespace=True, min_length=1)]
    objectives: List[LessonObjective]
    assessment: Assessment
    sections: List[LessonSection]
    extension: ExtensionTask
    homework: HomeworkTask
    notes: List[constr(strip_whitespace=True, min_length=1)]
    materials: List[constr(strip_whitespace=True, min_length=1)]


class LessonBundle(BaseModel):
    """Wrapper for returning multiple variants in a single payload."""

    model_config = ConfigDict(protected_namespaces=(), populate_by_name=True)
    schema_id: Literal["toon.bundle.v1"] = Field("toon.bundle.v1", alias="schema")
    variants: List[LessonPlan]


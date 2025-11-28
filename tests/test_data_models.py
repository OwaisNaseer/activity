"""Unit tests for data models (Pydantic validation)."""
import pytest
from pydantic import ValidationError

from services.data_models import (
    ActivityRequest,
    ActivityResponse,
    LessonPlan,
    LessonBundle,
    LessonMeta,
    LessonObjective,
    Assessment,
    AssessmentCriterion,
    LessonSection,
    LessonStep,
    ExtensionTask,
    HomeworkTask
)


class TestActivityRequest:
    """Test ActivityRequest model validation."""
    
    def test_valid_request(self):
        """Test that a valid request passes validation."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        assert request.subject == "Science"
        assert request.num_variants == 1
    
    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ActivityRequest(
                subject="Science",
                # Missing grade_band, topic_concept, etc.
            )
    
    def test_invalid_available_time(self):
        """Test that available_time must be > 0."""
        with pytest.raises(ValidationError):
            ActivityRequest(
                subject="Science",
                grade_band="5th grade",
                topic_concept="Robotics",
                available_time=0,  # Invalid
                output_language="English"
            )
    
    def test_num_variants_range(self):
        """Test that num_variants must be between 1 and 3."""
        # Valid
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=2
        )
        assert request.num_variants == 2
        
        # Invalid - too low
        with pytest.raises(ValidationError):
            ActivityRequest(
                subject="Science",
                grade_band="5th grade",
                topic_concept="Robotics",
                available_time=45,
                output_language="English",
                num_variants=0
            )
        
        # Invalid - too high
        with pytest.raises(ValidationError):
            ActivityRequest(
                subject="Science",
                grade_band="5th grade",
                topic_concept="Robotics",
                available_time=45,
                output_language="English",
                num_variants=4
            )


class TestLessonPlan:
    """Test LessonPlan model validation."""
    
    def test_valid_lesson_plan(self):
        """Test that a valid lesson plan passes validation."""
        meta = LessonMeta(
            subject="Science",
            grade_band="5th grade",
            topic="Robotics",
            available_time=45,
            language="English"
        )
        
        plan = LessonPlan(
            meta=meta,
            title="Test Lesson",
            key_points=["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
            objectives=[
                LessonObjective(label="Obj1", text="Learn robotics")
            ],
            assessment=Assessment(
                overview="Test assessment",
                criteria=[
                    AssessmentCriterion(focus="Test", detail="Test detail")
                ]
            ),
            sections=[
                LessonSection(
                    id="opening",
                    title="Opening",
                    goal="Start lesson",
                    steps=[
                        LessonStep(label="Step1", duration="5m", detail="Do something")
                    ]
                )
            ],
            extension=ExtensionTask(title="Extension", detail="Extension detail"),
            homework=HomeworkTask(prompt="Homework", deliverable="Report"),
            notes=["Note 1"],
            materials=["Material 1"]
        )
        
        assert plan.title == "Test Lesson"
        assert len(plan.key_points) == 5
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        meta = LessonMeta(
            subject="Science",
            grade_band="5th grade",
            topic="Robotics",
            available_time=45,
            language="English"
        )
        
        with pytest.raises(ValidationError):
            LessonPlan(
                meta=meta,
                # Missing title, key_points, etc.
            )
    
    def test_title_min_length(self):
        """Test that title must be at least 3 characters."""
        meta = LessonMeta(
            subject="Science",
            grade_band="5th grade",
            topic="Robotics",
            available_time=45,
            language="English"
        )
        
        with pytest.raises(ValidationError):
            LessonPlan(
                meta=meta,
                title="AB",  # Too short
                key_points=["Point 1"],
                objectives=[LessonObjective(label="Obj1", text="Text")],
                assessment=Assessment(
                    overview="Overview",
                    criteria=[AssessmentCriterion(focus="F", detail="D")]
                ),
                sections=[
                    LessonSection(
                        id="op",
                        title="Op",
                        goal="Go",
                        steps=[LessonStep(label="S", duration="5m", detail="D")]
                    )
                ],
                extension=ExtensionTask(title="E", detail="D"),
                homework=HomeworkTask(prompt="P", deliverable="D"),
                notes=["N"],
                materials=["M"]
            )


class TestActivityResponse:
    """Test ActivityResponse model."""
    
    def test_success_response(self):
        """Test successful response."""
        response = ActivityResponse(
            success=True,
            activity="Test activity"
        )
        assert response.success is True
        assert response.activity == "Test activity"
    
    def test_error_response(self):
        """Test error response."""
        response = ActivityResponse(
            success=False,
            error="Test error"
        )
        assert response.success is False
        assert response.error == "Test error"


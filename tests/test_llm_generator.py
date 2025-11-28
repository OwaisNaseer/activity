"""Unit tests for LLM generator (orchestration layer)."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import ValidationError

from services.data_models import ActivityRequest, LessonPlan, LessonMeta
from services.llm_generator import ActivityGenerator


class TestActivityGenerator:
    """Test ActivityGenerator orchestration."""
    
    @patch('services.llm_generator.LLMClient')
    def test_initialization(self, mock_client_class):
        """Test generator initialization."""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client_class.return_value = mock_client
        
        generator = ActivityGenerator()
        
        assert generator.llm_client is not None
        mock_client_class.assert_called_once()
    
    @patch('services.llm_generator.LLMClient')
    @patch('services.llm_generator.build_toon_prompt')
    def test_generate_activity_success(self, mock_build_prompt, mock_client_class):
        """Test successful activity generation."""
        # Setup mocks
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.generate.return_value = (
            True,
            "variants[1]{schema,meta,title,key_points}: toon.lesson.v1,meta{subject,grade_band},Test Lesson,key_points[5]{Point1,Point2,Point3,Point4,Point5}",
            None
        )
        mock_client_class.return_value = mock_client
        
        mock_build_prompt.return_value = "Test prompt"
        
        # Mock TOON parsing
        with patch('services.llm_generator.toon_to_json') as mock_toon_parse:
            mock_toon_parse.return_value = {
                "variants": [{
                    "schema": "toon.lesson.v1",
                    "meta": {
                        "subject": "Science",
                        "grade_band": "5th grade",
                        "topic": "Robotics",
                        "available_time": 45,
                        "language": "English"
                    },
                    "title": "Test Lesson",
                    "key_points": ["P1", "P2", "P3", "P4", "P5"],
                    "objectives": [{"label": "Obj1", "text": "Learn"}],
                    "assessment": {
                        "overview": "Test",
                        "criteria": [{"focus": "F", "detail": "D"}]
                    },
                    "sections": [{
                        "id": "op",
                        "title": "Op",
                        "goal": "Go",
                        "steps": [{"label": "S", "duration": "5m", "detail": "D"}]
                    }],
                    "extension": {"title": "E", "detail": "D"},
                    "homework": {"prompt": "P", "deliverable": "D"},
                    "notes": ["N"],
                    "materials": ["M"]
                }]
            }
            
            request = ActivityRequest(
                subject="Science",
                grade_band="5th grade",
                topic_concept="Robotics",
                available_time=45,
                output_language="English",
                num_variants=1
            )
            
            generator = ActivityGenerator()
            success, result, error = generator.generate_activity(request)
            
            assert success is True
            assert result is not None
            assert len(result) == 1
            assert error is None
    
    @patch('services.llm_generator.LLMClient')
    def test_generate_activity_fallback(self, mock_client_class):
        """Test fallback to template when LLM fails."""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = False
        mock_client_class.return_value = mock_client
        
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        
        generator = ActivityGenerator()
        success, result, error = generator.generate_activity(request)
        
        assert success is True
        assert result is not None
        assert len(result) == 1
        assert "Template" in error or "fallback" in error.lower()
    
    @patch('services.llm_generator.LLMClient')
    def test_parse_and_validate_valid_toon(self, mock_client_class):
        """Test parsing and validation of valid TOON data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        generator = ActivityGenerator()
        
        # Mock valid TOON data
        with patch('services.llm_generator.toon_to_json') as mock_toon_parse:
            mock_toon_parse.return_value = {
                "variants": [{
                    "schema": "toon.lesson.v1",
                    "meta": {
                        "subject": "Science",
                        "grade_band": "5th grade",
                        "topic": "Robotics",
                        "available_time": 45,
                        "language": "English"
                    },
                    "title": "Test Lesson",
                    "key_points": ["P1", "P2", "P3", "P4", "P5"],
                    "objectives": [{"label": "Obj1", "text": "Learn"}],
                    "assessment": {
                        "overview": "Test",
                        "criteria": [{"focus": "F", "detail": "D"}]
                    },
                    "sections": [{
                        "id": "op",
                        "title": "Op",
                        "goal": "Go",
                        "steps": [{"label": "S", "duration": "5m", "detail": "D"}]
                    }],
                    "extension": {"title": "E", "detail": "D"},
                    "homework": {"prompt": "P", "deliverable": "D"},
                    "notes": ["N"],
                    "materials": ["M"]
                }]
            }
            
            success, variants, error = generator._parse_and_validate_response(
                "test toon text",
                1
            )
            
            assert success is True
            assert variants is not None
            assert len(variants) == 1
    
    @patch('services.llm_generator.LLMClient')
    def test_parse_and_validate_invalid_data(self, mock_client_class):
        """Test parsing with invalid data that fails Pydantic validation."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        generator = ActivityGenerator()
        
        # Mock invalid TOON data (missing required fields)
        with patch('services.llm_generator.toon_to_json') as mock_toon_parse:
            mock_toon_parse.return_value = {
                "variants": [{
                    "title": "Incomplete Lesson"
                    # Missing required fields
                }]
            }
            
            success, variants, error = generator._parse_and_validate_response(
                "test toon text",
                1
            )
            
            assert success is False
            assert variants is None
            assert error is not None
            assert "validation" in error.lower() or "failed" in error.lower()
    
    @patch('services.llm_generator.LLMClient')
    def test_generate_activity_stream(self, mock_client_class):
        """Test streaming generation."""
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.generate_stream.return_value = iter(["chunk1", "chunk2", "chunk3"])
        mock_client_class.return_value = mock_client
        
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        
        generator = ActivityGenerator()
        chunks = list(generator.generate_activity_stream(request))
        
        assert len(chunks) == 3
        assert "chunk1" in chunks
    
    @patch('services.llm_generator.LLMClient')
    def test_build_template_plan(self, mock_client_class):
        """Test template plan generation."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        
        generator = ActivityGenerator()
        plan = generator._build_template_plan(request, 0)
        
        assert isinstance(plan, LessonPlan)
        assert plan.title == "Robotics Lesson Blueprint (Variant 1)"
        assert len(plan.key_points) == 5
        assert plan.meta.subject == "Science"


"""Unit tests for prompt builder."""
import pytest

from services.data_models import ActivityRequest
from services.prompt_builder import build_toon_prompt


class TestPromptBuilder:
    """Test prompt building functionality."""
    
    def test_build_toon_prompt_basic(self):
        """Test basic prompt building."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        
        prompt = build_toon_prompt(request)
        
        assert "TOON" in prompt
        assert "Science" in prompt
        assert "Robotics" in prompt
        assert "5th grade" in prompt
        assert "45" in prompt
    
    def test_build_toon_prompt_with_standard(self):
        """Test prompt building with standard."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            standard="NGSS",
            num_variants=1
        )
        
        prompt = build_toon_prompt(request)
        
        assert "NGSS" in prompt
        assert "standard" in prompt.lower()
    
    def test_build_toon_prompt_multiple_variants(self):
        """Test prompt building for multiple variants."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=3
        )
        
        prompt = build_toon_prompt(request)
        
        assert "variants[3]" in prompt
        assert "Generate exactly 3 variant(s)" in prompt
    
    def test_build_toon_prompt_other_language(self):
        """Test prompt building with 'Other' language option."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="Other",
            language="Spanish",
            num_variants=1
        )
        
        prompt = build_toon_prompt(request)
        
        # Should use the 'language' field when output_language is "Other"
        assert "Spanish" in prompt or "spanish" in prompt.lower()
    
    def test_build_toon_prompt_with_materials(self):
        """Test prompt building with materials."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            available_materials="LEGO, sensors, motors",
            num_variants=1
        )
        
        prompt = build_toon_prompt(request)
        
        assert "LEGO" in prompt or "materials" in prompt.lower()
    
    def test_build_toon_prompt_structure(self):
        """Test that prompt has correct structure."""
        request = ActivityRequest(
            subject="Science",
            grade_band="5th grade",
            topic_concept="Robotics",
            available_time=45,
            output_language="English",
            num_variants=1
        )
        
        prompt = build_toon_prompt(request)
        
        # Check for key sections
        assert "INPUT (TOON):" in prompt
        assert "OUTPUT:" in prompt
        assert "RULES:" in prompt
        assert "Begin TOON response:" in prompt


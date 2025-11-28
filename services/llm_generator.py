"""Main orchestration service for activity generation.

This module implements the ActivityGenerator class which orchestrates the
entire flow: Request -> Prompt Builder -> LLM Client -> Parser/Validator -> Response.

It handles error handling, fallbacks, and validation using Pydantic V2.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple, Iterator

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
from services.prompt_builder import build_toon_prompt
from services.llm_client import LLMClient
from utils.toon_utils import toon_to_json

logger = logging.getLogger(__name__)


class ActivityGenerator:
    """Main service for generating activities using LLM.
    
    This class orchestrates the complete generation flow:
    1. Receives ActivityRequest
    2. Builds TOON prompt using PromptBuilder
    3. Calls LLM via LLMClient
    4. Parses TOON response
    5. Validates with Pydantic models
    6. Returns structured LessonPlan objects
    
    It includes comprehensive error handling and fallback mechanisms.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None
    ) -> None:
        """Initialize ActivityGenerator.
        
        Args:
            api_key: Optional OpenAI API key (defaults to env var)
            model: Optional model name (defaults to env var)
            temperature: Optional temperature (defaults to env var)
            base_url: Optional base URL (defaults to env var)
        """
        self.llm_client = LLMClient(
            api_key=api_key,
            model=model,
            temperature=temperature,
            base_url=base_url
        )
        logger.info("ActivityGenerator initialized")
    
    def generate_activity(
        self,
        request: ActivityRequest
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Generate activity description using LLM.
        
        This is the main public interface for activity generation. It handles
        the complete flow including error handling and fallbacks.
        
        Args:
            request: ActivityRequest model with all input parameters
            
        Returns:
            Tuple of (success: bool, variants: Optional[List[Dict]], error: Optional[str])
            - success: True if generation succeeded
            - variants: List of lesson plan dicts if successful, None otherwise
            - error: Error message if failed, None otherwise
        """
        try:
            num_variants = request.num_variants
            
            # Check if LLM is configured
            if not self.llm_client.is_configured():
                logger.warning("LLM not configured, using template response")
                return self._generate_template_response(request, num_variants)
            
            # Build the prompt
            try:
                prompt = build_toon_prompt(request)
                logger.debug(f"Built prompt ({len(prompt)} characters)")
            except Exception as prompt_error:
                logger.error(f"Error building prompt: {str(prompt_error)}", exc_info=True)
                # Fall back to template
                return self._generate_template_response(request, num_variants)
            
            # Generate with LLM
            try:
                logger.info(f"Generating {num_variants} structured variant(s) using LLM...")
                
                success, raw_response, error = self.llm_client.generate(prompt)
                
                if not success or not raw_response:
                    logger.warning(f"LLM generation failed: {error}")
                    return self._generate_template_response(request, num_variants)
                
                # LLM returns TOON format - parse, validate, and return clean JSON
                if raw_response:
                    logger.info(f"✓ Successfully received TOON response ({len(raw_response)} chars)")
                    
                    # Parse and validate TOON response
                    parse_success, structured_variants, parse_error = self._parse_and_validate_response(
                        raw_response,
                        num_variants
                    )
                    
                    if parse_success and structured_variants:
                        logger.info(
                            f"✓ Successfully parsed and validated {len(structured_variants)} variant(s) from TOON"
                        )
                        # Return clean JSON dicts (validated with Pydantic)
                        return True, structured_variants, None
                    
                    logger.warning(f"TOON parsing/validation failed: {parse_error}")
                    
                    # If parsing failed, try generating additional variants if needed
                    if num_variants > 1 and len(structured_variants or []) < num_variants:
                        # Generate remaining variants with temperature variation
                        for variant_idx in range(len(structured_variants or []), num_variants):
                            temp_variation = self.llm_client.temperature + (variant_idx * 0.1)
                            logger.info(f"Generating variant {variant_idx + 1}/{num_variants} with temperature {temp_variation:.2f}")
                            
                            variant_success, variant_response, variant_error = self.llm_client.generate(
                                prompt,
                                temperature=temp_variation
                            )
                            
                            if variant_success and variant_response:
                                var_parse_success, var_structured, var_parse_error = self._parse_and_validate_response(
                                    variant_response,
                                    1
                                )
                                if var_parse_success and var_structured:
                                    structured_variants.extend(var_structured)
                                    logger.info(f"✓ Successfully generated and validated variant {variant_idx + 1}")
                                else:
                                    logger.warning(f"Failed to parse variant {variant_idx + 1}: {var_parse_error}")
                            else:
                                logger.warning(f"Failed to generate variant {variant_idx + 1}: {variant_error}")
                        
                        if structured_variants and len(structured_variants) > 0:
                            return True, structured_variants, None
                    
                    # Fall back to template if parsing failed
                    return self._generate_template_response(request, num_variants)
                
                logger.warning("Empty response from LLM")
                return self._generate_template_response(request, num_variants)
                
            except Exception as llm_error:
                logger.error(
                    f"LLM API exception: {type(llm_error).__name__}: {str(llm_error)}",
                    exc_info=True
                )
                # Fall back to template
                return self._generate_template_response(request, num_variants)
            
        except Exception as e:
            logger.error(f"Error generating activity: {str(e)}", exc_info=True)
            # Always return template as fallback
            try:
                return self._generate_template_response(request, request.num_variants)
            except Exception as template_error:
                logger.error(f"Even template generation failed: {str(template_error)}")
                return False, None, f"Error generating activity: {str(e)}"
    
    def generate_activity_stream(
        self,
        request: ActivityRequest
    ) -> Iterator[str]:
        """Generate activity with streaming support.
        
        Args:
            request: ActivityRequest model with all input parameters
            
        Yields:
            str: Chunks of generated TOON text as they arrive
            "ERROR: <message>": Error message if generation fails
        """
        # Check if LLM is configured
        if not self.llm_client.is_configured():
            yield "ERROR: LLM client is not configured (missing API key or client)"
            return
        
        # Build the prompt
        try:
            prompt = build_toon_prompt(request)
        except Exception as prompt_error:
            logger.error(f"Error building prompt: {str(prompt_error)}")
            yield f"ERROR: Error building prompt: {str(prompt_error)}"
            return
        
        # Stream from LLM
        for chunk in self.llm_client.generate_stream(prompt):
            yield chunk
    
    def _parse_and_validate_response(
        self,
        raw_text: str,
        expected_variants: int
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Parse TOON response and validate with Pydantic models.
        
        This method:
        1. Parses TOON format to Python dict
        2. Validates against LessonPlan Pydantic model
        3. Returns serialized dicts for frontend consumption
        
        Args:
            raw_text: Raw TOON text from LLM
            expected_variants: Expected number of variants
            
        Returns:
            Tuple of (success: bool, variants: Optional[List[Dict]], error: Optional[str])
        """
        # Try TOON format first (primary method)
        try:
            logger.debug("Attempting TOON format parsing...")
            toon_data = toon_to_json(raw_text)
            logger.info("Successfully decoded TOON format response")
            
            # Extract variants from TOON structure (professional parsing)
            if "variants" in toon_data and isinstance(toon_data["variants"], list):
                variants_data = toon_data["variants"]
                logger.debug(f"Found {len(variants_data)} variants in 'variants' key")
            elif isinstance(toon_data, list):
                variants_data = toon_data
                logger.debug(f"TOON data is a list with {len(variants_data)} items")
            elif isinstance(toon_data, dict) and "schema" in toon_data:
                # Single lesson plan object with schema
                variants_data = [toon_data]
                logger.debug("TOON data is a single lesson plan object")
            else:
                # Root is the lesson or unknown structure
                variants_data = [toon_data] if toon_data else []
                logger.debug(f"Using root as single variant (type: {type(toon_data)})")
            
            if not variants_data:
                return False, None, "No variants in TOON response"
            
            # Validate each variant with Pydantic
            validated_variants: List[Dict[str, Any]] = []
            for idx, variant_data in enumerate(variants_data[:expected_variants]):
                try:
                    # Validate against LessonPlan Pydantic model
                    lesson_plan = LessonPlan.model_validate(variant_data)
                    # Serialize to dict for frontend consumption
                    validated_variants.append(lesson_plan.model_dump(by_alias=True))
                    logger.debug(f"✓ Validated variant {idx + 1} with Pydantic")
                except ValidationError as validation_error:
                    logger.warning(
                        f"Pydantic validation failed for variant {idx + 1}: {validation_error}"
                    )
                    # Try to continue with other variants
                    continue
            
            if validated_variants:
                return True, validated_variants, None
            else:
                return False, None, "All variants failed Pydantic validation"
            
        except Exception as toon_error:
            logger.debug(f"TOON parsing failed: {toon_error}, trying JSON fallback")
            
            # Fallback to JSON parsing
            try:
                import json
                json_str = self._extract_json(raw_text)
                payload = json.loads(json_str)
                logger.info("Successfully parsed JSON format response (fallback)")
                
                # Extract variants from JSON
                if "variants" in payload:
                    variants_data = payload["variants"]
                else:
                    variants_data = [payload]
                
                if not variants_data:
                    return False, None, "No variants in JSON payload"
                
                # Validate each variant with Pydantic
                validated_variants: List[Dict[str, Any]] = []
                for idx, variant_data in enumerate(variants_data[:expected_variants]):
                    try:
                        lesson_plan = LessonPlan.model_validate(variant_data)
                        validated_variants.append(lesson_plan.model_dump(by_alias=True))
                        logger.debug(f"✓ Validated variant {idx + 1} with Pydantic (JSON fallback)")
                    except ValidationError as validation_error:
                        logger.warning(
                            f"Pydantic validation failed for variant {idx + 1}: {validation_error}"
                        )
                        continue
                
                if validated_variants:
                    return True, validated_variants, None
                else:
                    return False, None, "All variants failed Pydantic validation (JSON fallback)"
                
            except Exception as json_error:
                logger.error(
                    f"Both TOON and JSON parsing failed. TOON: {toon_error}, JSON: {json_error}"
                )
                return (
                    False,
                    None,
                    f"Failed to parse response. TOON error: {toon_error}, JSON error: {json_error}"
                )
    
    @staticmethod
    def _extract_json(raw_text: str) -> str:
        """Extract JSON from text, removing code fences if present.
        
        Args:
            raw_text: Raw text potentially containing JSON
            
        Returns:
            Extracted JSON string
            
        Raises:
            ValueError: If JSON braces not found
        """
        # Remove markdown code fences
        if "```" in raw_text:
            start = raw_text.find("```")
            end = raw_text.rfind("```")
            if start != -1 and end != -1 and end > start:
                raw_text = raw_text[start + 3 : end]
        
        # Extract JSON object
        first_brace = raw_text.find("{")
        last_brace = raw_text.rfind("}")
        
        if first_brace == -1 or last_brace == -1:
            raise ValueError("JSON braces not found in model response")
        
        return raw_text[first_brace : last_brace + 1]
    
    def _generate_template_response(
        self,
        request: ActivityRequest,
        num_variants: int
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """Generate a structured template when LLM fails.
        
        This is a fallback mechanism that generates deterministic lesson plans
        when the LLM is unavailable or fails.
        
        Args:
            request: ActivityRequest model
            num_variants: Number of variants to generate
            
        Returns:
            Tuple of (success: bool, variants: List[Dict], error: Optional[str])
        """
        variants: List[Dict[str, Any]] = []
        for idx in range(num_variants):
            template_plan = self._build_template_plan(request, idx)
            # Convert to dict for consistency
            variants.append(template_plan.model_dump(by_alias=True))
        
        return True, variants, "Template response used due to generator fallback"
    
    def _build_template_plan(
        self,
        request: ActivityRequest,
        variant_index: int
    ) -> LessonPlan:
        """Build a deterministic LessonPlan for fallback scenarios.
        
        Args:
            request: ActivityRequest model
            variant_index: Index of this variant (0-based)
            
        Returns:
            Validated LessonPlan model
        """
        # Extract data from request
        subject = request.subject
        grade_band = request.grade_band
        topic = request.topic_concept
        available_time = request.available_time
        language = request.output_language
        
        # Handle "Other" language
        if language == "Other":
            language = request.language or "English"
        
        materials = self._split_materials(request.available_materials)
        constraints = request.constraints or "None listed"
        
        # Build metadata
        meta = LessonMeta(
            subject=subject,
            grade_band=grade_band,
            topic=topic,
            available_time=available_time,
            language=language,
            standard=request.standard,
            constraints=constraints,
        )
        
        # Build objectives
        objectives = [
            LessonObjective(
                label="Obj1",
                text=f"Students will explain the core ideas of {topic}."
            ),
            LessonObjective(
                label="Obj2",
                text=f"Students will apply {topic} by building a quick demonstration."
            ),
        ]
        
        # Build assessment
        assessment = Assessment(
            overview=(
                "Teams present a working demo, submit a brief explanation, "
                "and receive rubric-based feedback."
            ),
            criteria=[
                AssessmentCriterion(
                    focus="Prototype",
                    detail="Demonstrates the target concept reliably."
                ),
                AssessmentCriterion(
                    focus="Documentation",
                    detail="Clear explanation of choices and safety considerations."
                ),
                AssessmentCriterion(
                    focus="Reflection",
                    detail="Team reflects on improvements and constraints."
                ),
            ],
        )
        
        # Build sections
        sections = [
            LessonSection(
                id="opening",
                title="Opening",
                goal="Launch curiosity and set expectations.",
                steps=[
                    LessonStep(
                        label="Hook",
                        duration="2m",
                        detail=f"Quick demo or question to connect with {topic}."
                    ),
                    LessonStep(
                        label="Goal",
                        duration="2m",
                        detail="State outcomes and success criteria."
                    ),
                    LessonStep(
                        label="Roles",
                        duration="3m",
                        detail="Assign team roles and clarify expectations."
                    ),
                ],
            ),
            LessonSection(
                id="introduction",
                title="Introduction to New Material",
                goal="Model the core knowledge required for the build.",
                steps=[
                    LessonStep(
                        label="Key Idea",
                        duration="5m",
                        detail=f"Mini-lesson on fundamental {topic} concepts."
                    ),
                    LessonStep(
                        label="Materials",
                        duration="3m",
                        detail=(
                            f"Show how to use {', '.join(materials) if materials else 'available materials'} "
                            "safely."
                        )
                    ),
                    LessonStep(
                        label="Misconception",
                        duration="3m",
                        detail="Surface and correct a likely misconception."
                    ),
                ],
            ),
            LessonSection(
                id="guided_practice",
                title="Guided Practice",
                goal="Rehearse core moves with coaching.",
                steps=[
                    LessonStep(
                        label="Walkthrough",
                        duration="10m",
                        detail="Teacher-led build of a mini-example."
                    ),
                    LessonStep(
                        label="Checklist",
                        duration="5m",
                        detail="Teams verify understanding with prompts and probes."
                    ),
                ],
            ),
            LessonSection(
                id="independent_practice",
                title="Independent Practice",
                goal="Teams complete the primary challenge.",
                steps=[
                    LessonStep(
                        label="Build Sprint",
                        duration=f"{available_time - 20}m",
                        detail="Teams construct, test, and iterate."
                    ),
                    LessonStep(
                        label="Deliverables",
                        duration="5m",
                        detail="Prototype, one-page explanation, quick stand-up."
                    ),
                ],
            ),
            LessonSection(
                id="closing",
                title="Closing",
                goal="Synthesize learning and preview next steps.",
                steps=[
                    LessonStep(
                        label="Share-out",
                        duration="5m",
                        detail="Teams name a success and a challenge."
                    ),
                    LessonStep(
                        label="Restate Objective",
                        duration="2m",
                        detail="Teacher connects evidence back to objectives and assessment."
                    ),
                ],
            ),
        ]
        
        # Build extension and homework
        extension = ExtensionTask(
            title="Extension Challenge",
            detail="Early finishers add a secondary feature, test it, and document trade-offs.",
        )
        
        homework = HomeworkTask(
            prompt="Reflect on collaboration, technical hurdles, and next improvements.",
            deliverable="Short journal entry or video note highlighting one insight.",
        )
        
        # Build notes
        notes = [
            f"Constraints to honor: {constraints}.",
            "Adapt pacing as needed for class context.",
        ]
        
        # Build and return LessonPlan
        return LessonPlan(
            meta=meta,
            title=f"{topic} Lesson Blueprint (Variant {variant_index + 1})",
            key_points=[
                f"Fundamentals related to {topic}",
                "Practical application and hands-on learning",
                "Design process and documentation",
                "Safety and classroom management",
                f"Core concepts and principles of {topic}",
            ],
            objectives=objectives,
            assessment=assessment,
            sections=sections,
            extension=extension,
            homework=homework,
            notes=notes,
            materials=materials if materials else ["General classroom supplies"],
        )
    
    @staticmethod
    def _split_materials(raw: Optional[str]) -> List[str]:
        """Split materials string into list.
        
        Args:
            raw: Raw materials string (comma-separated) or None
            
        Returns:
            List of material strings
        """
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        return [item.strip() for item in raw.split(",") if item.strip()]


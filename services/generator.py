import json
import os
import logging
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import ValidationError

from utils.toon_utils import json_to_toon, toon_to_json

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Lazy import of openai to avoid import errors if package is not installed
_openai = None

def _get_openai():
    """Lazy import of openai module"""
    global _openai
    if _openai is None:
        try:
            import openai
            _openai = openai
        except ImportError as e:
            logger.error(f"Failed to import openai: {str(e)}")
            raise ImportError("openai package is not installed. Please install it with: pip install openai")
    return _openai

# TOON schema identifiers (for reference in prompts)
LESSON_SCHEMA = "toon.lesson.v1"
BUNDLE_SCHEMA = "toon.bundle.v1"


class ActivityGenerator:
    """Service for generating activities using OpenAI API"""
    
    def __init__(self):
        # Try to import openai
        try:
            openai = _get_openai()
        except ImportError as e:
            logger.error(f"OpenAI import failed: {str(e)}")
            self.api_key = None
            self.model = None
            self.temperature = None
            self.base_url = None
            self.client = None
            return
        
        # OpenAI Configuration
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables!")
        else:
            logger.info(f"OpenAI API - Key loaded: {self.api_key[:10]}...")
            logger.info(f"OpenAI Model: {self.model}")
            logger.info(f"OpenAI Temperature: {self.temperature}")
            logger.info(f"OpenAI Base URL: {self.base_url}")
        
        # Initialize OpenAI client
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("✓ OpenAI client initialized")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
    
    def generate_activity(self, request_data: dict) -> tuple[bool, Optional[List[dict]], Optional[str]]:
        """
        Generate activity description using OpenAI API
        
        Returns:
            tuple: (success: bool, activity/activities: str or List[str] or None, error: str or None)
            - For num_variants=1: returns (bool, str, str)
            - For num_variants>1: returns (bool, List[str], str)
        """
        try:
            # Always ensure we have valid request_data
            if not request_data:
                request_data = {}
            
            num_variants = request_data.get("num_variants", 1)
            if num_variants < 1 or num_variants > 3:
                num_variants = 1
            
            # If OpenAI is not configured, return template response
            if not self.api_key or not self.client:
                logger.warning("OpenAI not configured, using template response")
                return self._generate_template_response(request_data, num_variants)
            
            # Build the prompt
            try:
                prompt = self._build_toon_prompt(request_data)
            except Exception as prompt_error:
                logger.error(f"Error building prompt: {str(prompt_error)}")
                # Fall back to template
                return self._generate_template_response(request_data, num_variants)
            
            # Try to generate with OpenAI
            try:
                logger.info(f"Generating {num_variants} structured variant(s) using OpenAI API...")
                logger.info(
                    "Generator state - API Key: %s, Client: %s",
                    "Set" if self.api_key else "Not set",
                    "Initialized" if self.client else "Not initialized",
                )

                result = self._generate_with_openai(prompt)
                
                if result and len(result) >= 3 and result[0] and result[1]:
                    parse_success, structured_variants, parse_error = self._parse_toon_response(result[1], num_variants)
                    if parse_success:
                        logger.info("✓ Successfully parsed %s variant(s) from TOON/JSON response", len(structured_variants))
                        return True, structured_variants, None

                    logger.warning(f"TOON/JSON parsing failed: {parse_error}")
                    return self._generate_template_response(request_data, num_variants)

                error_detail = result[2] if result and len(result) > 2 else "Unknown error"
                logger.warning(f"OpenAI generation failed, using template. Error: {error_detail}")
                return self._generate_template_response(request_data, num_variants)
                        
            except Exception as openai_error:
                logger.error(f"OpenAI API exception: {type(openai_error).__name__}: {str(openai_error)}", exc_info=True)
                # Fall back to template
                logger.warning("Falling back to template response due to exception")
                return self._generate_template_response(request_data, num_variants)
            
        except Exception as e:
            logger.error(f"Error generating activity: {str(e)}", exc_info=True)
            # Always return template as fallback
            try:
                num_variants = request_data.get("num_variants", 1) if request_data else 1
                return self._generate_template_response(request_data, num_variants)
            except Exception as template_error:
                logger.error(f"Even template generation failed: {str(template_error)}")
                # Last resort - return a basic error
                return False, None, f"Error generating activity: {str(e)}"
    
    def _build_toon_prompt(self, data: dict) -> str:
        """Build TOON-format prompt: JSON → TOON → LLM.
        
        Converts request data to TOON format for token-efficient LLM communication.
        """
        subject = data.get("subject", "N/A")
        grade_band = data.get("grade_band", "N/A")
        topic = data.get("topic_concept", "N/A")
        materials = data.get("available_materials", "Not specified")
        constraints = data.get("constraints", "None specified")
        available_time = data.get("available_time", 0)
        language = data.get("output_language", "English")
        standard = data.get("standard", "")
        num_variants = data.get("num_variants", 1)
        
        if language == "Other":
            language = data.get("language", "English") or "English"
        
        # Convert request to TOON format
        # TOON (Token-Oriented Object Notation) spec: https://github.com/toon-format/spec
        # Python library: https://github.com/toon-format/toon
        # Example: {"name": "Alice", "age": 30} → "name: Alice\nage: 30"
        # Arrays: users[2]{id,name}: 1,Alice\n2,Bob
        request_dict = {
            "subject": subject,
            "grade_band": grade_band,
            "topic": topic,
            "available_time": available_time,
            "materials": materials,
            "constraints": constraints,
            "language": language,
            "standard": standard,
            "num_variants": num_variants
        }
        
        try:
            # Uses toon.encode() from the official toon library
            toon_input = json_to_toon(request_dict)
        except Exception as e:
            logger.warning(f"Failed to encode TOON input: {e}, using fallback")
            # Simple fallback
            toon_input = f"subject: {subject}\ngrade_band: {grade_band}\ntopic: {topic}\navailable_time: {available_time}\nmaterials: {materials}\nconstraints: {constraints}\nlanguage: {language}\nstandard: {standard}\nnum_variants: {num_variants}"
        
        standard_note = f" If standard '{standard}' is provided, mention it professionally in notes." if standard else ""
        
        # Simple TOON output example
        prompt = f"""You are an expert instructional designer. Use TOON (Token-Oriented Object Notation) format.

INPUT (TOON):
{toon_input}

OUTPUT: Respond in TOON format with this structure:
variants[{num_variants}]{{schema,meta,title,key_points,objectives,assessment,sections,extension,homework,notes,materials}}:
  toon.lesson.v1,meta{{subject,grade_band,topic,available_time,language,standard,constraints}},string,key_points[5]{{string}},objectives[]{{label,text}},assessment{{overview,criteria[]{{focus,detail}}}},sections[]{{id,title,goal,steps[]{{label,duration,detail}}}},extension{{title,detail}},homework{{prompt,deliverable}},notes[]{{string}},materials[]{{string}}

RULES:
- Respond ONLY in TOON format. No JSON, no markdown, no prose.
- Respond in {language} with concise, professional sentences.
- key_points: Exactly 5 items covering: fundamentals, practical application, design process, documentation, safety/classroom management.
- Keep tokens minimal: short labels, focused details.{standard_note}
- Generate exactly {num_variants} variant(s).

Begin TOON response:"""
        
        return prompt.strip()
    
    def _generate_with_openai_stream(self, prompt: str, temperature: Optional[float] = None):
        """Generate text using OpenAI API with streaming.
        
        Yields:
            str: Chunks of generated text as they arrive
        """
        try:
            if not self.client:
                yield "ERROR: OpenAI client is not initialized"
                return
            
            if not self.api_key:
                yield "ERROR: OPENAI_API_KEY is not configured"
                return
            
            use_temperature = temperature if temperature is not None else self.temperature
            
            logger.info(f"Streaming from OpenAI API with model: {self.model}, temperature: {use_temperature}")
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert instructional designer who outputs only valid TOON (Token-Oriented Object Notation) format following the provided schema. No JSON, no markdown, only TOON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=use_temperature,
                max_tokens=2500,
                stream=True
            )
            
            accumulated_text = ""
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        accumulated_text += content
                        yield content
            
            logger.info(f"✓ Streamed {len(accumulated_text)} characters")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"OpenAI Streaming Error - Type: {error_type}, Message: {error_msg}")
            yield f"ERROR: {error_msg}"
    
    def _generate_with_openai(self, prompt: str, temperature: Optional[float] = None) -> tuple[bool, Optional[str], Optional[str]]:
        """Generate text using OpenAI API
        
        Args:
            prompt: The prompt to send to OpenAI
            temperature: Optional temperature override (defaults to self.temperature)
        """
        try:
            # Check if client is available
            if not self.client:
                error_msg = "OpenAI client is not initialized"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Check if API key is set
            if not self.api_key:
                error_msg = "OPENAI_API_KEY is not configured"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Use provided temperature or default
            use_temperature = temperature if temperature is not None else self.temperature
            
            logger.info(f"Calling OpenAI API with model: {self.model}, temperature: {use_temperature}, base_url: {self.base_url}")
            logger.info(f"API Key present: {bool(self.api_key)}, Key prefix: {self.api_key[:10] if self.api_key else 'N/A'}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert instructional designer who outputs only valid TOON (Token-Oriented Object Notation) format following the provided schema. No JSON, no markdown, only TOON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=use_temperature,
                max_tokens=2500
            )
            
            logger.info(f"OpenAI API response received: {type(response)}")
            
            if response and response.choices and len(response.choices) > 0:
                generated_text = response.choices[0].message.content.strip()
                
                if generated_text:
                    logger.info(f"✓ Generated {len(generated_text)} characters")
                    return True, generated_text, None
                else:
                    error_msg = "OpenAI returned empty text"
                    logger.warning(error_msg)
                    return False, None, error_msg
            else:
                error_msg = "OpenAI returned no results (empty choices)"
                logger.warning(error_msg)
                return False, None, error_msg
                
        except Exception as e:
            # Log detailed error information
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"OpenAI API Error - Type: {error_type}, Message: {error_msg}")
            logger.error(f"Full error details: {repr(e)}")
            
            # Provide more specific error messages based on error type
            if "authentication" in error_msg.lower() or "api key" in error_msg.lower() or "401" in error_msg:
                detailed_error = f"OpenAI API authentication failed. Please check your API key. Error: {error_msg}"
            elif "rate limit" in error_msg.lower() or "429" in error_msg:
                detailed_error = f"OpenAI API rate limit exceeded. Please try again later. Error: {error_msg}"
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = f"OpenAI model not found. Check if model '{self.model}' is available. Error: {error_msg}"
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                detailed_error = f"Network error connecting to OpenAI API. Check your internet connection and base_url. Error: {error_msg}"
            else:
                detailed_error = f"OpenAI API error ({error_type}): {error_msg}"
            
            logger.error(detailed_error)
            return False, None, detailed_error
    
    def _parse_toon_response(self, raw_text: str, expected_variants: int) -> tuple[bool, Optional[List[dict]], Optional[str]]:
        """Parse TOON response from LLM: TOON → JSON (dict).
        
        Simple flow: LLM returns TOON → decode to dict → return dicts.
        Falls back to JSON parsing if TOON decode fails.
        """
        # Try TOON format first (primary method)
        try:
            toon_data = toon_to_json(raw_text)
            logger.info("Successfully decoded TOON format response")
            
            # Extract variants from TOON structure
            if "variants" in toon_data:
                variants_data = toon_data["variants"]
            elif "lesson" in toon_data:
                variants_data = toon_data["lesson"] if isinstance(toon_data["lesson"], list) else [toon_data["lesson"]]
            else:
                # Single lesson object or root is the lesson
                variants_data = [toon_data] if toon_data else []
            
            if not variants_data:
                return False, None, "No variants in TOON response"
            
            # Return dicts (limit to expected variants)
            serialized = [dict(v) for v in variants_data[:expected_variants]]
            return True, serialized, None
            
        except Exception as toon_error:
            logger.debug(f"TOON parsing failed: {toon_error}, trying JSON fallback")
            
            # Fallback to JSON parsing
            try:
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
                
                serialized = [dict(v) for v in variants_data[:expected_variants]]
                return True, serialized, None
                
            except Exception as json_error:
                logger.error(f"Both TOON and JSON parsing failed. TOON: {toon_error}, JSON: {json_error}")
                return False, None, f"Failed to parse response. TOON error: {toon_error}, JSON error: {json_error}"

    @staticmethod
    def _extract_json(raw_text: str) -> str:
        """Remove code fences and isolate the JSON object."""
        if "```" in raw_text:
            start = raw_text.find("```")
            end = raw_text.rfind("```")
            if start != -1 and end != -1 and end > start:
                raw_text = raw_text[start + 3 : end]
        
        first_brace = raw_text.find("{")
        last_brace = raw_text.rfind("}")
        
        if first_brace == -1 or last_brace == -1:
            raise ValueError("JSON braces not found in model response")
        
        return raw_text[first_brace : last_brace + 1]

    def _generate_template_response(self, data: dict, num_variants: int = 1) -> tuple[bool, Optional[List[dict]], Optional[str]]:
        """Generate a structured template when OpenAI fails."""
        variants = []
        for idx in range(num_variants):
            variants.append(self._build_template_plan(data, idx))
        
        return True, variants, "Template response used due to generator fallback"

    def _build_template_plan(self, data: dict, variant_index: int) -> dict:
        """Build a deterministic LessonPlan for fallback scenarios."""
        subject = data.get("subject", "Subject")
        grade_band = data.get("grade_band", "Grade")
        topic = data.get("topic_concept", "Topic")
        available_time = data.get("available_time", 45)
        language = data.get("output_language", "English")
        materials = self._split_materials(data.get("available_materials", ""))
        constraints = data.get("constraints", "None listed")
        
        meta = LessonMeta(
            subject=subject,
            grade_band=grade_band,
            topic=topic,
            available_time=available_time,
            language=language,
            standard=data.get("standard"),
            constraints=constraints,
        )
        
        objectives = [
            LessonObjective(label="Obj1", text=f"Students will explain the core ideas of {topic}."),
            LessonObjective(label="Obj2", text=f"Students will apply {topic} by building a quick demonstration."),
        ]
        
        assessment = Assessment(
            overview="Teams present a working demo, submit a brief explanation, and receive rubric-based feedback.",
            criteria=[
                AssessmentCriterion(focus="Prototype", detail="Demonstrates the target concept reliably."),
                AssessmentCriterion(focus="Documentation", detail="Clear explanation of choices and safety considerations."),
                AssessmentCriterion(focus="Reflection", detail="Team reflects on improvements and constraints."),
            ],
        )
        
        sections = [
            LessonSection(
                id="opening",
                title="Opening",
                goal="Launch curiosity and set expectations.",
                steps=[
                    LessonStep(label="Hook", duration="2m", detail=f"Quick demo or question to connect with {topic}."),
                    LessonStep(label="Goal", duration="2m", detail="State outcomes and success criteria."),
                    LessonStep(label="Roles", duration="3m", detail="Assign team roles and clarify expectations."),
                ],
            ),
            LessonSection(
                id="introduction",
                title="Introduction to New Material",
                goal="Model the core knowledge required for the build.",
                steps=[
                    LessonStep(label="Key Idea", duration="5m", detail=f"Mini-lesson on fundamental {topic} concepts."),
                    LessonStep(label="Materials", duration="3m", detail=f"Show how to use {', '.join(materials) or 'available materials'} safely."),
                    LessonStep(label="Misconception", duration="3m", detail="Surface and correct a likely misconception."),
                ],
            ),
            LessonSection(
                id="guided_practice",
                title="Guided Practice",
                goal="Rehearse core moves with coaching.",
                steps=[
                    LessonStep(label="Walkthrough", duration="10m", detail="Teacher-led build of a mini-example."),
                    LessonStep(label="Checklist", duration="5m", detail="Teams verify understanding with prompts and probes."),
                ],
            ),
            LessonSection(
                id="independent_practice",
                title="Independent Practice",
                goal="Teams complete the primary challenge.",
                steps=[
                    LessonStep(label="Build Sprint", duration=f"{available_time - 20}m", detail="Teams construct, test, and iterate."),
                    LessonStep(label="Deliverables", duration="5m", detail="Prototype, one-page explanation, quick stand-up."),
                ],
            ),
            LessonSection(
                id="closing",
                title="Closing",
                goal="Synthesize learning and preview next steps.",
                steps=[
                    LessonStep(label="Share-out", duration="5m", detail="Teams name a success and a challenge."),
                    LessonStep(label="Restate Objective", duration="2m", detail="Teacher connects evidence back to objectives and assessment."),
                ],
            ),
        ]
        
        extension = ExtensionTask(
            title="Extension Challenge",
            detail="Early finishers add a secondary feature, test it, and document trade-offs.",
        )
        
        homework = HomeworkTask(
            prompt="Reflect on collaboration, technical hurdles, and next improvements.",
            deliverable="Short journal entry or video note highlighting one insight.",
        )
        
        notes = [
            f"Constraints to honor: {constraints}.",
            "Adapt pacing as needed for class context.",
        ]
        
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
            materials=materials or ["General classroom supplies"],
        )

    @staticmethod
    def _split_materials(raw: Optional[str]) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return raw
        return [item.strip() for item in raw.split(",") if item.strip()]

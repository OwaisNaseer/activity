import os
import logging
from typing import Optional
from dotenv import load_dotenv

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
    
    def generate_activity(self, request_data: dict) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Generate activity description using OpenAI API
        
        Returns:
            tuple: (success: bool, activity: str or None, error: str or None)
        """
        try:
            # Always ensure we have valid request_data
            if not request_data:
                request_data = {}
            
            # If OpenAI is not configured, return template response
            if not self.api_key or not self.client:
                logger.warning("OpenAI not configured, using template response")
                return self._generate_template_response(request_data)
            
            # Build the prompt
            try:
                prompt = self._build_prompt(request_data)
            except Exception as prompt_error:
                logger.error(f"Error building prompt: {str(prompt_error)}")
                # Fall back to template
                return self._generate_template_response(request_data)
            
            # Try to generate with OpenAI
            try:
                logger.info("Generating activity using OpenAI API...")
                logger.info(f"Generator state - API Key: {'Set' if self.api_key else 'Not set'}, Client: {'Initialized' if self.client else 'Not initialized'}")
                
                result = self._generate_with_openai(prompt)
                
                if result and len(result) >= 3 and result[0] and result[1]:
                    logger.info("✓ Successfully generated activity using OpenAI!")
                    return result
                else:
                    error_detail = result[2] if result and len(result) > 2 else 'Unknown error'
                    logger.warning(f"OpenAI generation failed, using template. Error: {error_detail}")
                    # Log the error but still return template
                    logger.warning("Falling back to template response due to OpenAI failure")
                    return self._generate_template_response(request_data)
            except Exception as openai_error:
                logger.error(f"OpenAI API exception: {type(openai_error).__name__}: {str(openai_error)}", exc_info=True)
                # Fall back to template
                logger.warning("Falling back to template response due to exception")
                return self._generate_template_response(request_data)
            
        except Exception as e:
            logger.error(f"Error generating activity: {str(e)}", exc_info=True)
            # Always return template as fallback
            try:
                return self._generate_template_response(request_data)
            except Exception as template_error:
                logger.error(f"Even template generation failed: {str(template_error)}")
                # Last resort - return a basic error
                return False, None, f"Error generating activity: {str(e)}"
    
    def _build_prompt(self, data: dict) -> str:
        """Build a detailed prompt for OpenAI to generate lesson plan"""
        subject = data.get("subject", "N/A")
        grade_band = data.get("grade_band", "N/A")
        topic = data.get("topic_concept", "N/A")
        materials = data.get("available_materials", "Not specified")
        constraints = data.get("constraints", "None specified")
        available_time = data.get("available_time", 0)
        language = data.get("output_language", "English")
        
        # Map language names to language instructions
        language_instructions = {
            "English": "in English",
            "Spanish": "in Spanish (en español)",
            "French": "in French (en français)",
            "German": "in German (auf Deutsch)",
            "Italian": "in Italian (in italiano)",
            "Portuguese": "in Portuguese (em português)",
            "Chinese": "in Chinese (用中文)",
            "Japanese": "in Japanese (日本語で)",
            "Other": "in the requested language"
        }
        lang_instruction = language_instructions.get(language, f"in {language}")

        prompt = f"""You are an expert instructional designer. Generate a comprehensive, professional lesson plan in the EXACT format specified below.

IMPORTANT: Write the ENTIRE response {lang_instruction}. All content must be in {language}.

Subject: {subject}
Grade/Band: {grade_band}
Topic/Concept: {topic}
Available Materials: {materials}
Constraints: {constraints}
Available Time: {available_time} minutes
Output Language: {language} (MUST write in {language})

Generate a detailed lesson plan following this EXACT structure and format. Write everything {lang_instruction}:

# [Lesson Title: {topic}]

## LEARNING OBJECTIVE
[Write a clear, measurable learning objective. Students will...]

## ASSESSMENT
[Describe how students will demonstrate mastery. Include: working prototype/demonstration, written explanation, rubric-based assessment covering reliability, component interaction, and justification of choices/safety considerations.]

## KEY POINTS
- [Core concept 1: e.g., Fundamentals related to the topic]
- [Core concept 2: e.g., Practical application and hands-on learning]
- [Core concept 3: e.g., Design process and documentation]
- [Core concept 4: e.g., Safety and classroom management]
- [Core concept 5: Add more as appropriate for the topic]

## OPENING
- **Hook (1-2 minutes)**: [Brief video/demo or engaging introduction]
- **Goal Explanation**: [Explain the lesson's goal and what students will accomplish]
- **Group Organization**: [Organize students into groups of 3-4 with assigned roles: project manager, builder, programmer, tester/documenter]
- **Anticipatory Question**: [Pose a question to engage students]

## INTRODUCTION TO NEW MATERIAL
[5-8 minutes per mini-topic]
- **Key Concepts**: [Explain main concepts related to {topic}]
- **Materials Overview**: [Explain how to use: {materials}]
- **Basic Principles**: [Explain fundamental principles]
- **Active Learning**: [Include hands-on activity or demonstration]
- **Common Misconception**: [Address a common misconception about the topic]

## GUIDED PRACTICE
- **Behavioral Expectations**: [Set clear expectations for student behavior]
- **Component Identification (5 minutes)**: [Activity to identify key elements]
- **Simple Activity Build (10 minutes)**: [Step-by-step activity building]
- **Practice Exercise (10-15 minutes)**: [Guided practice with teacher support and guiding questions]
- **Task Challenge Introduction (10 minutes)**: [Introduce the main challenge with success criteria and model timeline]
- **Monitoring**: [Use checklist and probing questions to monitor student performance]

## INDEPENDENT PRACTICE
- **Behavioral Expectations**: [Set expectations for collaborative work]
- **Assignment**: [Teams design and complete the main activity]
- **Deliverables**: 
  - Working prototype or completed work
  - One-page design explanation
  - Team demonstration
- **Timeline**: [Adapt for {available_time} minute lesson or split across two class periods]
- **Teacher Support**: [Mini-lessons and rubric for formative feedback]

## CLOSING
- **Exit Activity**: [Quick activity where teams share success/challenge]
- **Restatement**: [Restate learning objective and assessment criteria]

## EXTENSION ACTIVITY
[For early finishers: Add a secondary objective or challenge with documentation and testing]

## HOMEWORK
[Individual reflection/journal on activity behavior, technical challenges, and potential improvements with additional resources]

## STANDARDS ALIGNED
- **Relevant Standards**: [List applicable educational standards for {subject} at {grade_band} level]
- **Note**: [Adapt materials and recommendations as needed based on: {constraints}]

REMEMBER: Write EVERYTHING in {language}. Use the EXACT materials specified: {materials}. Consider these constraints: {constraints}. Make it appropriate for {grade_band} grade level and {available_time} minutes duration."""
        return prompt
    
    def _generate_with_openai(self, prompt: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Generate text using OpenAI API"""
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
            
            logger.info(f"Calling OpenAI API with model: {self.model}, base_url: {self.base_url}")
            logger.info(f"API Key present: {bool(self.api_key)}, Key prefix: {self.api_key[:10] if self.api_key else 'N/A'}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert instructional designer who creates comprehensive, well-structured lesson plans for educators."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=4000
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
    
    def _generate_template_response(self, data: dict) -> tuple[bool, Optional[str], Optional[str]]:
        """Generate a template-based response when OpenAI fails"""
        activity = f"""# {data.get('topic_concept', 'Lesson Plan')}

## LEARNING OBJECTIVE
Students will understand the key concepts of {data.get('topic_concept', 'the topic')} and apply their knowledge through hands-on activities.

## ASSESSMENT
Students will demonstrate mastery through:
- Working prototype or demonstration
- Written explanation of their work
- Rubric-based assessment covering reliability, component interaction, and justification of choices

## KEY POINTS
- Core concepts related to {data.get('topic_concept', 'the topic')}
- Practical application and hands-on learning
- Design process and documentation
- Safety considerations

## OPENING
- **Hook (1-2 minutes)**: Brief introduction to engage students
- **Goal Explanation**: Explain what students will accomplish
- **Group Organization**: Organize students into groups with assigned roles
- **Anticipatory Question**: Pose an engaging question

## INTRODUCTION TO NEW MATERIAL
Introduce key concepts and materials needed for the activity.

## GUIDED PRACTICE
Scaffolded activities with teacher facilitation and support.

## INDEPENDENT PRACTICE
Students work in teams to complete the main activity.

## CLOSING
Review key concepts and assess understanding.

## EXTENSION ACTIVITY
Additional challenges for early finishers.

## HOMEWORK
Reflection and journaling on the activity.

## STANDARDS ALIGNED
Relevant educational standards for this lesson.

*Note: This is a template-based response generated because OpenAI API call failed.*"""
        
        return True, activity, None

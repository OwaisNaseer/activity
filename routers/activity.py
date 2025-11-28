from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging
import json
import asyncio
import random
from services.data_models import ActivityRequest, ActivityResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy import and initialization of generator to avoid import errors at module load time
_generator = None
_generator_error = None


def lesson_plan_to_markdown(plan_data: dict) -> str:
    """Render a lesson plan dict (from TOON/JSON) into the legacy markdown format.
    
    Works with plain dicts - no Pydantic models required.
    """
    if not plan_data or not isinstance(plan_data, dict):
        logger.error("Invalid plan_data: must be a dict")
        logger.error(f"plan_data type: {type(plan_data)}, value: {str(plan_data)[:200]}")
        return ""
    
    # Log what we're working with
    logger.debug(f"Converting plan_data with keys: {list(plan_data.keys())}")

    def find_section(section_id: str):
        sections = plan_data.get("sections", [])
        for section in sections:
            if isinstance(section, dict) and section.get("id") == section_id:
                return section
        return None

    def get_step_detail(section, label_contains: str, default_detail: str):
        if not section:
            return default_detail
        steps = section.get("steps", [])
        for step in steps:
            if isinstance(step, dict):
                label = step.get("label", "")
                if label_contains.lower() in label.lower():
                    return step.get("detail", default_detail)
        return default_detail

    opening = find_section("opening")
    introduction = find_section("introduction")
    guided = find_section("guided_practice")
    independent = find_section("independent_practice")
    closing = find_section("closing")

    meta = plan_data.get("meta", {})
    title = plan_data.get("title", "Lesson Plan")
    objectives = plan_data.get("objectives", [])
    assessment = plan_data.get("assessment", {})
    key_points = plan_data.get("key_points", [])
    extension = plan_data.get("extension", {})
    homework = plan_data.get("homework", {})
    materials = plan_data.get("materials", [])

    lines = [f"# [Lesson Title: {title}]", ""]

    # Learning objectives
    lines.append("## LEARNING OBJECTIVE")
    if objectives and isinstance(objectives, list) and len(objectives) > 0:
        first_obj = objectives[0] if isinstance(objectives[0], dict) else {"text": str(objectives[0])}
        lines.append(first_obj.get("text", ""))
    lines.append("")

    # Assessment
    lines.append("## ASSESSMENT")
    if isinstance(assessment, dict):
        lines.append(assessment.get("overview", ""))
        criteria = assessment.get("criteria", [])
        for criterion in criteria:
            if isinstance(criterion, dict):
                lines.append(f"- {criterion.get('detail', '')}")
    lines.append("")

    # Key points (show all, typically 5)
    lines.append("## KEY POINTS")
    for point in key_points[:5]:  # Limit to 5
        lines.append(f"- {point}")
    lines.append("")

    # Opening
    lines.append("## OPENING")
    lines.append(f"- **Hook (1-2 minutes)**: {get_step_detail(opening, 'Hook', 'Engage students with a quick demo tied to the topic.')}")
    lines.append(f"- **Goal Explanation**: {get_step_detail(opening, 'Goal', 'Explain what learners will accomplish and why it matters.')}")
    lines.append(f"- **Group Organization**: {get_step_detail(opening, 'Roles', 'Assign collaborative roles and clarify expectations.')}")
    lines.append(f"- **Anticipatory Question**: {get_step_detail(opening, 'Question', 'Prompt students with a question that previews the challenge.')}")
    lines.append("")

    # Introduction to new material
    topic = meta.get("topic", "")
    lines.append("## INTRODUCTION TO NEW MATERIAL")
    lines.append("- **Key Concepts**: " + get_step_detail(introduction, "Key", f"Highlight essential ideas for {topic}."))
    materials_str = ', '.join(materials) if materials else "available materials"
    lines.append("- **Materials Overview**: " + get_step_detail(introduction, "Materials", f"Model how to use {materials_str} safely and effectively."))
    lines.append("- **Basic Principles**: " + get_step_detail(introduction, "Principle", "Review foundational knowledge students must recall."))
    lines.append("- **Active Learning**: " + get_step_detail(introduction, "Active", "Facilitate a short, hands-on mini task."))
    lines.append("- **Common Misconception**: " + get_step_detail(introduction, "Misconception", "Address a misconception before it appears in student work."))
    lines.append("")

    # Guided practice
    lines.append("## GUIDED PRACTICE")
    lines.append("- **Behavioral Expectations**: " + get_step_detail(guided, "Behavior", "Clarify collaboration and safety norms."))
    lines.append("- **Component Identification (5 minutes)**: " + get_step_detail(guided, "Component", "Teams identify each part they will need."))
    lines.append("- **Simple Activity Build (10 minutes)**: " + get_step_detail(guided, "Walkthrough", "Demonstrate a pared-down version of the activity."))
    lines.append("- **Practice Exercise (10-15 minutes)**: " + get_step_detail(guided, "Practice", "Guide teams through a scaffolded rehearsal with checkpoints."))
    lines.append("- **Task Challenge Introduction (10 minutes)**: " + get_step_detail(guided, "Challenge", "Define success criteria, deliverables, and timeline."))
    lines.append("- **Monitoring**: " + get_step_detail(guided, "Monitor", "Use a checklist and probing questions to provide feedback."))
    lines.append("")

    # Independent practice
    available_time = meta.get("available_time", 45)
    lines.append("## INDEPENDENT PRACTICE")
    lines.append("- **Behavioral Expectations**: " + get_step_detail(independent, "Behavior", "Reinforce teamwork, safety, and respectful feedback."))
    lines.append("- **Assignment**: " + get_step_detail(independent, "Build", "Teams execute the full build or investigation."))
    lines.append("- **Deliverables**: ")
    lines.append("  - Working prototype or completed work")
    lines.append("  - One-page design explanation")
    lines.append("  - Team demonstration")
    lines.append(f"- **Timeline**: {get_step_detail(independent, 'Timeline', f'Use the remaining {available_time} minutes or split across two sessions.')}")
    lines.append("- **Teacher Support**: " + get_step_detail(independent, "Support", "Offer mini-lessons, checklists, and formative feedback."))
    lines.append("")

    # Closing
    lines.append("## CLOSING")
    lines.append("- **Exit Activity**: " + get_step_detail(closing, "Share", "Quick share-out highlighting a success and a challenge."))
    lines.append("- **Restatement**: " + get_step_detail(closing, "Restate", "Link student evidence back to the learning objective and assessment."))
    lines.append("")

    # Extension
    lines.append("## EXTENSION ACTIVITY")
    if isinstance(extension, dict):
        lines.append(extension.get("detail", ""))
    lines.append("")

    # Homework
    lines.append("## HOMEWORK")
    if isinstance(homework, dict):
        lines.append(homework.get("prompt", ""))
    lines.append("")

    # Standards aligned / notes
    lines.append("## STANDARDS ALIGNED")
    standard_align_text = ""
    standard = meta.get("standard", "")
    if standard and str(standard).strip():
        standard_align_text = f" that align with: {standard}"
    constraints_text = meta.get("constraints", "class constraints")
    subject = meta.get("subject", "Subject")
    grade_band = meta.get("grade_band", "Grade")
    lines.append(f"- **Relevant Standards**: [List applicable educational standards for {subject} at {grade_band} level{standard_align_text}]")
    lines.append(f"- **Note**: [Adapt materials and recommendations as needed based on: {constraints_text}]")

    return "\n".join(lines).strip()


def _generate_fallback_markdown(variant_dict: dict) -> str:
    """Generate a basic markdown from variant dict even if structure is incomplete."""
    lines = []
    
    title = variant_dict.get("title", "Lesson Plan")
    lines.append(f"# [Lesson Title: {title}]")
    lines.append("")
    
    # Try to extract any available data
    meta = variant_dict.get("meta", {})
    if isinstance(meta, dict):
        topic = meta.get("topic", variant_dict.get("topic", "Topic"))
        subject = meta.get("subject", "Subject")
        grade_band = meta.get("grade_band", "Grade")
    else:
        topic = variant_dict.get("topic", "Topic")
        subject = variant_dict.get("subject", "Subject")
        grade_band = variant_dict.get("grade_band", "Grade")
    
    # Learning Objective
    lines.append("## LEARNING OBJECTIVE")
    objectives = variant_dict.get("objectives", [])
    if objectives and isinstance(objectives, list) and len(objectives) > 0:
        if isinstance(objectives[0], dict):
            lines.append(objectives[0].get("text", f"Students will learn about {topic}."))
        else:
            lines.append(str(objectives[0]))
    else:
        lines.append(f"Students will learn about {topic}.")
    lines.append("")
    
    # Assessment
    lines.append("## ASSESSMENT")
    assessment = variant_dict.get("assessment", {})
    if isinstance(assessment, dict):
        lines.append(assessment.get("overview", "Students will demonstrate understanding through practical application."))
    else:
        lines.append("Students will demonstrate understanding through practical application.")
    lines.append("")
    
    # Key Points
    lines.append("## KEY POINTS")
    key_points = variant_dict.get("key_points", [])
    if key_points:
        for point in key_points[:5]:
            lines.append(f"- {point}")
    else:
        lines.append(f"- Fundamentals of {topic}")
        lines.append("- Practical application")
        lines.append("- Design process")
    lines.append("")
    
    # Add a note about incomplete data
    lines.append("## NOTE")
    lines.append("This lesson plan was generated from available data. Some sections may need manual completion.")
    lines.append("")
    
    return "\n".join(lines).strip()


def get_generator(force_reload=False):
    """Lazy load the generator to avoid import errors at module load time
    
    Args:
        force_reload: If True, reload environment variables and reinitialize generator
    """
    global _generator, _generator_error
    
    # Force reload if requested (useful when .env changes)
    if force_reload:
        logger.info("Forcing generator reload...")
        _generator = None
        _generator_error = None
        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(override=True)
    
    if _generator is not None:
        return _generator
    
    if _generator_error is not None and not force_reload:
        return None
    
    try:
        from services.llm_generator import ActivityGenerator
        _generator = ActivityGenerator()
        logger.info("ActivityGenerator initialized successfully")
        # Check if LLM client is configured
        if _generator.llm_client.is_configured():
            logger.info("LLM client is configured")
        else:
            logger.warning("LLM client is NOT configured - will use template responses")
        return _generator
    except ImportError as e:
        _generator_error = f"Failed to import generator: {str(e)}"
        logger.error(_generator_error, exc_info=True)
        return None
    except Exception as e:
        _generator_error = f"Failed to initialize ActivityGenerator: {str(e)}"
        logger.error(_generator_error, exc_info=True)
        return None

@router.post("/generate-activity", response_model=ActivityResponse)
async def generate_activity(request: ActivityRequest):
    """
    Generate a professional activity description based on input parameters
    """
    try:
        # Get generator (lazy load) - try to reload if no API key
        generator = get_generator()
        
        # If generator exists but LLM client is not configured, try to reload
        if generator and not generator.llm_client.is_configured():
            logger.info("Generator LLM client not configured, attempting to reload...")
            generator = get_generator(force_reload=True)
        
        # Check if generator is available
        if generator is None:
            error_msg = _generator_error or "Generator service is not available. Please check server configuration."
            logger.error(f"ActivityGenerator is not available: {error_msg}")
            return ActivityResponse(
                success=False,
                activity=None,
                error=error_msg
            )
        
        # Log the request with full details
        logger.info("=" * 60)
        logger.info("ACTIVITY GENERATION REQUEST RECEIVED")
        logger.info(f"  Subject: {request.subject}")
        logger.info(f"  Grade/Band: {request.grade_band}")
        logger.info(f"  Topic/Concept: {request.topic_concept}")
        logger.info(f"  Available Time: {request.available_time} minutes")
        logger.info(f"  Output Language: {request.output_language}")
        logger.info(f"  Materials: {request.available_materials or 'Not specified'}")
        logger.info(f"  Constraints: {request.constraints or 'None specified'}")
        logger.info(f"  Standard: {request.standard or 'Not specified'}")
        logger.info(f"  Language (Other): {request.language or 'N/A'}")
        logger.info(f"  Number of Variants: {request.num_variants}")
        logger.info(f"  Regenerate: {request.regenerate}")
        logger.info("=" * 60)
        
        # Validate input
        if not request.subject or not request.topic_concept:
            logger.warning("Validation failed: Subject or Topic/Concept missing")
            return ActivityResponse(
                success=False,
                activity=None,
                error="Subject and Topic/Concept are required"
            )
        
        if request.available_time <= 0:
            logger.warning("Validation failed: Invalid available_time")
            return ActivityResponse(
                success=False,
                activity=None,
                error="Available time must be greater than 0"
            )
        
        # Generate activity - pass ActivityRequest model directly
        num_variants = request.num_variants or 1
        try:
            logger.info("Calling generator.generate_activity...")
            logger.info(f"Generator state check - LLM configured: {generator.llm_client.is_configured()}")
            
            # Pass ActivityRequest model directly (new modular structure)
            success, result, error = generator.generate_activity(request)
            
            if isinstance(result, list):
                logger.info(f"Generator returned: success={success}, num_items={len(result)}, error={error}")
            else:
                logger.info(f"Generator returned: success={success}, type={type(result)}, error={error}")
            
            # If generation failed, log the error for debugging
            if not success and error:
                logger.error(f"Generation failed with error: {error}")
                # Include the error in the response so frontend can show it
                # But still return the template activity if available
                if result:
                    logger.info("Template activity was generated, returning it with error message")
        except Exception as gen_error:
            logger.error(f"Exception during generation: {str(gen_error)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            success, result, error = False, None, f"Generation error: {str(gen_error)}"
        
        # Return response - ensure all fields are properly set
        try:
            if success and result:
                # Result is now clean JSON dicts (validated with Pydantic) from TOON parsing
                if isinstance(result, list) and result and isinstance(result[0], dict):
                    logger.info(f"Structured activities generated successfully ({len(result)} variants)")
                    # Convert validated JSON dicts to markdown for frontend (maintains compatibility)
                    markdown_variants = []
                    for variant_dict in result:
                        markdown = lesson_plan_to_markdown(variant_dict)
                        markdown_variants.append(markdown)
                    
                    if num_variants == 1:
                        return ActivityResponse(
                            success=True,
                            activity=markdown_variants[0] if markdown_variants else "",
                            activities=None,
                            structured_activities=result,  # Also include clean JSON
                            error=None
                        )
                    else:
                        return ActivityResponse(
                            success=True,
                            activity=None,
                            activities=markdown_variants,  # Markdown for frontend
                            structured_activities=result,  # Clean JSON for structured access
                            error=error
                        )
                # Fallback for other result types
                if isinstance(result, list):
                    logger.info(f"Text activities generated successfully ({len(result)} variants)")
                    return ActivityResponse(
                        success=True,
                        activity=None,
                        activities=[str(item) for item in result],
                        error=error
                    )
                activity_str = str(result) if result else ""
                if not activity_str:
                    return ActivityResponse(
                        success=False,
                        activity=None,
                        activities=None,
                        structured_activities=None,
                        error="Generated activity is empty"
                    )
                return ActivityResponse(
                    success=True,
                    activity=activity_str,
                    activities=None,
                    structured_activities=None,
                    error=None
                )
            else:
                error_msg = str(error) if error else "Failed to generate activity"
                logger.error(f"Failed to generate activity: {error_msg}")
                
                # If we have a template activity but generation failed, return it with the error
                if result:
                    logger.info("Returning template activity with error message for user awareness")
                    if isinstance(result, list):
                        if isinstance(result, list) and result and isinstance(result[0], dict):
                            markdown_variants = [lesson_plan_to_markdown(item) for item in result]
                            return ActivityResponse(
                                success=True,
                                activity=markdown_variants[0] if len(markdown_variants) == 1 else None,
                                activities=markdown_variants if len(markdown_variants) > 1 else None,
                                structured_activities=result,
                                error=f"Note: {error_msg}"
                            )
                        return ActivityResponse(
                            success=True,
                            activity=None,
                            activities=[str(item) for item in result] if isinstance(result, list) else None,
                            structured_activities=None,
                            error=f"Note: {error_msg}"
                        )
                    else:
                        return ActivityResponse(
                            success=True,
                            activity=str(result),
                            activities=None,
                            structured_activities=None,
                            error=f"Note: {error_msg}"
                        )
                else:
                    return ActivityResponse(
                        success=False,
                        activity=None,
                        activities=None,
                        structured_activities=None,
                        error=error_msg
                    )
        except Exception as resp_error:
            logger.error(f"Error creating response: {str(resp_error)}", exc_info=True)
            # Last resort - return a basic response
            return ActivityResponse(
                success=False,
                activity=None,
                error=f"Response creation error: {str(resp_error)}"
            )
            
    except HTTPException as he:
        # Re-raise HTTP exceptions (like 400 Bad Request) - but wrap in ActivityResponse for this endpoint
        logger.warning(f"HTTPException raised: {he.detail}")
        return ActivityResponse(
            success=False,
            activity=None,
            error=he.detail
        )
    except Exception as e:
        logger.error(f"Unexpected error in generate_activity endpoint: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Always return ActivityResponse, never raise 500
        try:
            return ActivityResponse(
                success=False,
                activity=None,
                error=f"Internal server error: {str(e)}"
            )
        except Exception as final_error:
            # If even ActivityResponse fails, return dict (shouldn't happen)
            logger.critical(f"CRITICAL: Cannot create ActivityResponse: {str(final_error)}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "activity": None,
                    "error": f"Critical error: {str(e)}"
                }
            )


def stream_markdown_word_by_word(text: str):
    """Generator that yields markdown text word by word for natural streaming display."""
    words = text.split(' ')
    for i, word in enumerate(words):
        if i == 0:
            yield word
        else:
            yield ' ' + word


@router.post("/generate-activity-stream")
async def generate_activity_stream(request: ActivityRequest):
    """
    Generate activity with streaming response (Server-Sent Events).
    Streams the markdown output word-by-word for real-time display.
    """
    async def event_generator():
        try:
            # Get generator
            generator = get_generator()
            if generator is None:
                error_msg = _generator_error or "Generator service is not available"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                return
            
            # Validate input
            if not request.subject or not request.topic_concept:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Subject and Topic/Concept are required'})}\n\n"
                return
            
            if request.available_time <= 0:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Available time must be greater than 0'})}\n\n"
                return
            
            num_variants = request.num_variants or 1
            
            # Check if LLM is configured
            if not generator.llm_client.is_configured():
                logger.warning("LLM not configured, using template response")
                # Generate template and stream it
                success, result, error = generator._generate_template_response(request, num_variants)
                if success and result:
                    # Convert first variant to markdown and stream
                    markdown = lesson_plan_to_markdown(result[0] if isinstance(result, list) else result)
                    for chunk in stream_markdown_word_by_word(markdown):
                        if chunk:
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                            await asyncio.sleep(0.005)  # Faster delay for smooth streaming
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'content': error or 'Failed to generate template'})}\n\n"
                return
            
            # Generate multiple variants with real-time streaming (like OpenAI)
            num_variants = request.num_variants
            logger.info(f"Generating {num_variants} variant(s) with real-time streaming...")
            
            # Build TOON prompt once (for input extraction)
            try:
                from services.prompt_builder import build_toon_prompt
                toon_prompt = build_toon_prompt(request)
            except Exception as prompt_error:
                logger.error(f"Error building prompt: {str(prompt_error)}")
                yield f"data: {json.dumps({'type': 'error', 'content': f'Error building prompt: {str(prompt_error)}'})}\n\n"
                return
            
            # Extract TOON input section from prompt (everything before "OUTPUT:")
            toon_input_start = toon_prompt.find("INPUT (TOON")
            toon_input_end = toon_prompt.find("OUTPUT:", toon_input_start)
            if toon_input_start >= 0 and toon_input_end >= 0:
                toon_input_section = toon_prompt[toon_input_start:toon_input_end].strip()
            else:
                # Fallback: use full prompt if extraction fails
                toon_input_section = toon_prompt
            
            # Generate each variant with real-time streaming
            for variant_idx in range(num_variants):
                # Signal start of new variant
                if variant_idx > 0:
                    yield f"data: {json.dumps({'type': 'variant_separator', 'variant': variant_idx + 1, 'index': variant_idx, 'total': num_variants})}\n\n"
                
                # Show thinking/processing status before content starts
                yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...', 'variant': variant_idx + 1})}\n\n"
                yield f"data: {json.dumps({'type': 'status', 'content': f'Generating variant {variant_idx + 1} of {num_variants}...', 'variant': variant_idx + 1})}\n\n"
                
                # Use temperature variation for each variant (like old code)
                temp_variation = generator.llm_client.temperature + (variant_idx * 0.1)
                logger.info(f"Generating variant {variant_idx + 1} with temperature {temp_variation:.2f}")
                
                # Build streaming prompt: TOON input + markdown output (for real-time display)
                
                # Build markdown output prompt (same structure as old code)
                from services.prompt_builder import build_toon_prompt
                # Define recognized languages (same as prompt_builder)
                RECOGNIZED_LANGUAGES = {
                    "English", "Spanish", "French", "German", "Italian", "Portuguese",
                    "Chinese", "Japanese", "Korean", "Russian", "Arabic", "Hindi",
                    "Dutch", "Swedish", "Norwegian", "Danish", "Finnish", "Polish",
                    "Turkish", "Greek", "Hebrew", "Thai", "Vietnamese", "Indonesian",
                    "Czech", "Romanian", "Hungarian", "Bulgarian", "Croatian", "Serbian"
                }
                
                # Get language instruction - handle "Other" with validation
                language = request.output_language
                original_language = language
                if language == "Other":
                    custom_language = request.language or "English"
                    if not custom_language or custom_language.strip() == "":
                        language = "English"
                        logger.warning("Custom language was empty, defaulting to English")
                    else:
                        custom_language = custom_language.strip()
                        # Check if custom language is recognized
                        if custom_language not in RECOGNIZED_LANGUAGES:
                            logger.warning(
                                f"Custom language '{custom_language}' is not recognized. "
                                f"Falling back to English for reliable generation."
                            )
                            language = "English"
                        else:
                            language = custom_language
                
                # Map known languages to instructions
                lang_instructions = {
                    "English": "in English",
                    "Spanish": "in Spanish (en español)",
                    "French": "in French (en français)",
                    "German": "in German (auf Deutsch)",
                    "Italian": "in Italian (in italiano)",
                    "Portuguese": "in Portuguese (em português)",
                    "Chinese": "in Chinese (用中文)",
                    "Japanese": "in Japanese (日本語で)",
                }
                
                # If language is in the map, use the instruction; otherwise fall back to English
                if language in lang_instructions:
                    lang_instruction = lang_instructions[language]
                else:
                    # Language not recognized - fall back to English for safety
                    logger.warning(
                        f"Language '{language}' not in instruction map. "
                        f"Falling back to English for reliable generation."
                    )
                    language = "English"
                    lang_instruction = lang_instructions["English"]
                
                # Build streaming prompt: TOON input + markdown output instructions
                streaming_prompt = f"""You are an expert instructional designer. Generate a comprehensive, professional lesson plan in the EXACT format specified below.

{toon_input_section}

OUTPUT: Generate a detailed lesson plan following this EXACT structure and format. Write everything {lang_instruction}:

# [Lesson Title: {request.topic_concept}]

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

- **Key Concepts**: [Explain main concepts related to {request.topic_concept}]

- **Materials Overview**: [Explain how to use: {request.available_materials or "Not specified"}]

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

- **Timeline**: [Adapt for {request.available_time} minute lesson or split across two class periods]

- **Teacher Support**: [Mini-lessons and rubric for formative feedback]

## CLOSING

- **Exit Activity**: [Quick activity where teams share success/challenge]

- **Restatement**: [Restate learning objective and assessment criteria]

## EXTENSION ACTIVITY

[For early finishers: Add a secondary objective or challenge with documentation and testing]

## HOMEWORK

[Individual reflection/journal on activity behavior, technical challenges, and potential improvements with additional resources]

## STANDARDS ALIGNED

- **Relevant Standards**: [List applicable educational standards for {request.subject} at {request.grade_band} level{f" that align with: {request.standard}" if request.standard and request.standard.strip() else ""}]

- **Note**: [Adapt materials and recommendations as needed based on: {request.constraints or "None specified"}]

REMEMBER: Write EVERYTHING in {language}. All content, headings, and text must be in {language}. Use the EXACT materials specified: {request.available_materials or "Not specified"}. Consider these constraints: {request.constraints or "None specified"}. Make it appropriate for {request.grade_band} grade level and {request.available_time} minutes duration."""
                
                # Add language fallback note if language was changed from custom to English
                if original_language == "Other" and language == "English" and request.language and request.language.strip():
                    streaming_prompt += f"\n\nNOTE: The requested language '{request.language.strip()}' was not recognized. Content will be generated in English for reliability."
                
                # Override system message for streaming to request markdown output
                streaming_system_message = (
                    "You are an expert instructional designer who creates comprehensive, "
                    "well-structured lesson plans for educators."
                )
                
                try:
                    # Stream raw LLM chunks directly to frontend (real-time typing feel)
                    for chunk in generator.llm_client.generate_stream(
                        streaming_prompt, 
                        temperature=temp_variation,
                        system_message=streaming_system_message
                    ):
                        if chunk.startswith("ERROR:"):
                            logger.error(f"LLM stream error: {chunk}")
                            yield f"data: {json.dumps({'type': 'error', 'content': chunk, 'variant': variant_idx + 1})}\n\n"
                            break
                        
                        # Stream chunks directly to frontend (real-time, no delays)
                        if chunk:
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk, 'variant': variant_idx + 1})}\n\n"
                    
                    # Variant complete
                    yield f"data: {json.dumps({'type': 'variant_complete', 'variant': variant_idx + 1, 'index': variant_idx})}\n\n"
                    
                except Exception as stream_error:
                    logger.error(f"Error streaming variant {variant_idx + 1}: {str(stream_error)}", exc_info=True)
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Error streaming variant {variant_idx + 1}: {str(stream_error)}', 'variant': variant_idx + 1})}\n\n"
            
            # All variants complete
            yield f"data: {json.dumps({'type': 'done', 'total_variants': num_variants})}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': f'Streaming error: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


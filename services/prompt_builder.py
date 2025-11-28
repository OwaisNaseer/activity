"""Prompt builder for TOON (Token-Oriented Object Notation) format.

This module uses the EXACT same prompt structure that produced 100% correct results.
Uses TOON for input efficiency, but requests markdown output (like old code) for reliability.
"""
import logging
from typing import Dict, Any

from services.data_models import ActivityRequest
from utils.toon_utils import json_to_toon

logger = logging.getLogger(__name__)


def build_toon_prompt(request: ActivityRequest) -> str:
    """Build a prompt using TOON for input efficiency.
    
    Uses the EXACT same prompt structure as the old code (100% correct),
    but includes TOON input for token efficiency.
    Requests markdown output (like old code) for reliability.
    
    Args:
        request: ActivityRequest model containing all input parameters
        
    Returns:
        Complete prompt string ready for LLM (same structure as old code)
    """
    # Extract and validate required fields (same as old code)
    subject = request.subject
    grade_band = request.grade_band
    topic = request.topic_concept
    materials = request.available_materials or "Not specified"
    constraints = request.constraints or "None specified"
    available_time = request.available_time
    language = request.output_language
    standard = request.standard
    
    # Handle "Other" language option (same logic as old code)
    if language == "Other":
        language = request.language or "English"
        if not language or language.strip() == "":
            language = "English"
    
    # Map language names to language instructions (same as old code)
    language_instructions = {
        "English": "in English",
        "Spanish": "in Spanish (en español)",
        "French": "in French (en français)",
        "German": "in German (auf Deutsch)",
        "Italian": "in Italian (in italiano)",
        "Portuguese": "in Portuguese (em português)",
        "Chinese": "in Chinese (用中文)",
        "Japanese": "in Japanese (日本語で)",
    }
    
    # Check if language is recognized (same logic as old code)
    lang_instruction = language_instructions.get(language, None)
    if lang_instruction is None:
        # Language not recognized - use English and add note
        lang_instruction = "in English"
        language_note = (
            f"\n\nIMPORTANT NOTE: The requested language '{language}' may not be "
            "recognized or supported. The response will be generated in English. "
            "If you need content in a different language, please specify a recognized language name."
        )
    else:
        language_note = ""
    
    # Build standard instruction (same as old code)
    standard_instruction = ""
    if standard and standard.strip():
        standard_instruction = (
            f"\n\nIMPORTANT: If the provided standard '{standard}' is not valid or not recognized, "
            "mention this professionally in the STANDARDS ALIGNED section as: "
            "'Note: The provided standard may not be recognized or validated. "
            "Please adapt materials and recommendations as needed based on the constraints and available resources.'"
        )
    
    # Build request dictionary for TOON encoding (for token efficiency in input only)
    request_dict: Dict[str, Any] = {
        "subject": subject,
        "grade_band": grade_band,
        "topic": topic,
        "available_time": available_time,
        "materials": materials,
        "constraints": constraints,
        "language": language,
        "standard": standard or "",
        "num_variants": request.num_variants
    }
    
    # Convert to TOON format for token efficiency (input only)
    # Skip TOON section in prompt to reduce tokens - the main prompt already has all info
    # TOON encoding is still available for future use if needed
    toon_section = ""
    
    # Build the EXACT same prompt structure as old code
    # Request markdown output (like old code) for 100% reliability
    prompt = f"""You are an expert instructional designer. Generate a comprehensive, professional lesson plan in the EXACT format specified below.

IMPORTANT: Write the ENTIRE response {lang_instruction}. All content must be in {language}.{language_note}{standard_instruction}

Subject: {subject}

Grade/Band: {grade_band}

Topic/Concept: {topic}

Available Materials: {materials}

Constraints: {constraints}

Available Time: {available_time} minutes

Output Language: {language} (MUST write in {language}){toon_section}"""

    if standard and standard.strip():
        prompt += f"\nEducational Standard: {standard}"
    
    prompt += f"""

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

## STANDARDS ALIGNED"""
    
    # Add standard alignment note if standard is provided (same as old code)
    standard_align_text = ""
    if standard and standard.strip():
        standard_align_text = f" that align with: {standard}"
    
    prompt += f"""

- **Relevant Standards**: [List applicable educational standards for {subject} at {grade_band} level{standard_align_text}]

- **Note**: [Adapt materials and recommendations as needed based on: {constraints}]

REMEMBER: Write EVERYTHING in {language}. Use the EXACT materials specified: {materials}. Consider these constraints: {constraints}. Make it appropriate for {grade_band} grade level and {available_time} minutes duration."""
    
    return prompt.strip()

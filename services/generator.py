import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Try importing transformers for local GPT2
try:
    from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.error("transformers or torch not available - install with: pip install transformers torch")

class ActivityGenerator:
    """Service for generating activities using GPT2 locally (downloaded model)"""
    
    def __init__(self):
        # GPT2 from HuggingFace - downloaded locally
        self.hf_token = os.getenv("HUGGINGFACE_API_TOKEN", "")
        self.gpt2_model = "gpt2"
        
        # Local model and tokenizer
        self.model = None
        self.tokenizer = None
        self.generator = None
        self.model_loaded = False
        
        if not self.hf_token:
            logger.error("HUGGINGFACE_API_TOKEN not found in environment variables!")
        else:
            logger.info(f"GPT2 Local - Token loaded: {self.hf_token[:10]}...")
        
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers library not available! Install with: pip install transformers torch")
        else:
            logger.info("transformers library available - will load GPT2 locally")
    
    def _load_gpt2_model(self):
        """Load GPT2 model locally using your HuggingFace token"""
        if self.model_loaded:
            return True
        
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Cannot load GPT2 - transformers not available")
            return False
        
        try:
            logger.info("Downloading GPT2 model from HuggingFace (this may take a few minutes on first run)...")
            logger.info("Using your HuggingFace token for authentication...")
            
            # Load tokenizer with your token
            self.tokenizer = GPT2Tokenizer.from_pretrained(
                self.gpt2_model,
                token=self.hf_token if self.hf_token else None
            )
            logger.info("✓ Tokenizer loaded")
            
            # Load model with your token
            self.model = GPT2LMHeadModel.from_pretrained(
                self.gpt2_model,
                token=self.hf_token if self.hf_token else None
            )
            logger.info("✓ Model loaded")
            
            # Set model to evaluation mode
            self.model.eval()
            
            # Create text generation pipeline
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=-1  # Use CPU (change to 0 for GPU if available)
            )
            logger.info("✓ GPT2 pipeline created")
            
            self.model_loaded = True
            logger.info("✓ GPT2 model fully loaded and ready!")
            return True
            
        except Exception as e:
            logger.error(f"Error loading GPT2 model: {str(e)}")
            return False
    
    def generate_activity(self, request_data: dict) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Generate activity description using GPT2 locally
        
        Returns:
            tuple: (success: bool, activity: str or None, error: str or None)
        """
        try:
            # Load model if not already loaded
            if not self.model_loaded:
                logger.info("Loading GPT2 model...")
                if not self._load_gpt2_model():
                    return False, None, "Failed to load GPT2 model locally"
            
            # Build the prompt
            prompt = self._build_prompt(request_data)
            
            logger.info("Generating activity using local GPT2...")
            result = self._generate_with_gpt2(prompt)
            
            if result[0]:
                logger.info("✓ Successfully generated activity using local GPT2!")
                return result
            else:
                logger.error(f"GPT2 generation failed: {result[2]}")
                return self._generate_template_response(request_data)
            
        except Exception as e:
            logger.error(f"Error generating activity: {str(e)}")
            return False, None, f"Error generating activity: {str(e)}"
    
    def _build_prompt(self, data: dict) -> str:
        """Build a detailed prompt for GPT2"""
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

        # Calculate main activity time (ensure it's at least 5 minutes)
        main_activity_time = max(5, available_time - 10) if available_time > 10 else max(1, available_time - 5)

        prompt = f"""You are an expert instructional designer. Generate a professional educational activity description.

IMPORTANT: Write the ENTIRE response {lang_instruction}. All content must be in {language}.

Subject: {subject}
Grade/Band: {grade_band}
Topic/Concept: {topic}
Available Materials: {materials}
Constraints: {constraints}
Available Time: {available_time} minutes
Output Language: {language} (MUST write in {language})

Generate a detailed educational activity description. Use the EXACT materials specified: {materials}. Consider these constraints: {constraints}.

Return ONLY the activity in this EXACT format (write everything {lang_instruction}):

# Educational Activity: {topic}

## Subject: {subject}
## Grade/Band: {grade_band}
## Duration: {available_time} minutes

### Learning Objectives:
- [Write 3-5 clear, measurable learning objectives in {language}]

### Materials Needed:
- [List all materials. MUST use: {materials}]

### Activity Steps:
1. **Introduction (5 minutes)**: [Describe how to introduce the topic in {language}]
2. **Main Activity ({main_activity_time} minutes)**: [Provide detailed step-by-step instructions in {language}]
3. **Wrap-up (5 minutes)**: [Describe how to review and assess in {language}]

### Constraints Considered:
{constraints}

### Assessment:
- [List 2-4 assessment methods in {language}]

REMEMBER: Write EVERYTHING in {language}. Start now:"""
        return prompt
    
    def _generate_with_gpt2(self, prompt: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Generate text using local GPT2 model"""
        try:
            if not self.generator:
                return False, None, "GPT2 generator not initialized"
            
            logger.info("Running GPT2 inference locally...")
            
            # Calculate max length (cap at 1024 tokens for GPT2)
            prompt_tokens = len(prompt.split())
            max_length = min(prompt_tokens + 600, 1024)
            
            # Generate text with GPT2 - improved parameters
            results = self.generator(
                prompt,
                max_length=max_length,
                max_new_tokens=600,
                temperature=0.8,  # Slightly higher for more creativity
                do_sample=True,
                top_p=0.95,
                top_k=50,
                repetition_penalty=1.3,  # Higher to reduce repetition
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
            
            if results and len(results) > 0:
                generated_text = results[0].get("generated_text", "")
                
                # Extract only the new generated part (remove the prompt)
                if generated_text.startswith(prompt):
                    generated_text = generated_text[len(prompt):].strip()
                
                # Clean up the generated text
                generated_text = self._clean_generated_text(generated_text)
                
                if generated_text and generated_text.strip():
                    logger.info(f"✓ Generated {len(generated_text)} characters")
                    return True, generated_text.strip(), None
                else:
                    return False, None, "GPT2 generated empty text"
            else:
                return False, None, "GPT2 returned no results"
                
        except Exception as e:
            logger.error(f"Error generating with GPT2: {str(e)}")
            return False, None, f"GPT2 generation error: {str(e)}"
    
    def _clean_generated_text(self, text: str) -> str:
        """Clean and format the generated text"""
        if not text:
            return text
        
        # Remove any incomplete sentences at the end
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Remove lines that are just dashes or incomplete
                if not (line.startswith('-') and len(line) <= 3):
                    cleaned_lines.append(line)
        
        # Join lines and clean up extra whitespace
        cleaned = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        while '\n\n\n' in cleaned:
            cleaned = cleaned.replace('\n\n\n', '\n\n')
        
        return cleaned.strip()
    
    def _generate_template_response(self, data: dict) -> tuple[bool, Optional[str], Optional[str]]:
        """Generate a template-based response when GPT2 fails"""
        activity = f"""# Educational Activity: {data.get('topic_concept', 'Activity')}

## Subject: {data.get('subject', 'General')}
## Grade/Band: {data.get('grade_band', 'All Levels')}
## Duration: {data.get('available_time', 0)} minutes

### Learning Objectives:
- Students will understand the key concepts of {data.get('topic_concept', 'the topic')}
- Students will apply their knowledge through hands-on activities
- Students will demonstrate comprehension through assessment

### Materials Needed:
{data.get('available_materials', 'Standard classroom materials')}

### Activity Steps:
1. **Introduction (5 minutes)**: Introduce the topic and learning objectives
2. **Main Activity ({data.get('available_time', 30) - 10} minutes)**: Engage students in the core learning activity
3. **Wrap-up (5 minutes)**: Review key concepts and assess understanding

### Constraints Considered:
{data.get('constraints', 'None specified')}

### Assessment:
- Observe student participation and engagement
- Review completed work or responses
- Conduct a brief formative assessment

*Note: This is a template-based response generated locally because GPT2 generation failed.*"""
        
        return True, activity, None

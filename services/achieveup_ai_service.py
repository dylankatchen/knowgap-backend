# services/achieveup_ai_service.py

import logging
import json
import re
from typing import List, Dict, Any
from datetime import datetime, timezone
from config import Config
from utils.ai_utils import client, AI_MODEL

# Set up logging
logger = logging.getLogger(__name__)


async def analyze_questions(questions_data: List[Dict[str, Any]], course_skills: List[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze questions for skill mapping using batching for efficiency.
    """
    if not course_skills:
        raise ValueError("analyze_questions requires a non-empty course_skills list")

    if not Config.AI_API_KEY or not Config.AI_API_URL:
        raise RuntimeError("AI gateway key or URL is not set. Cannot analyze questions")

    results = []
    batch_size = 20

    # Batch AI processing (if enabled and needed)
    for i in range(0, len(questions_data), batch_size):
        chunk = questions_data[i : i + batch_size]
        chunk_texts = [
            (q.get('question_text', '') or q.get('text', ''))
            for q in chunk
        ]
            
        logger.info(f"Processing AI batch for {len(chunk_texts)} questions...")
        batch_results = await classify_questions_batch_ai(chunk_texts, course_skills)
            
        for j, question in enumerate(chunk):
            # batch_results is expected to be a dict or list mapping index to skills
            skills = batch_results.get(str(j)) or batch_results.get(j) or []
            results.append({
                'questionId': question.get('id'),
                'suggestedSkills': skills,
                'analysis_timestamp': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            })
            
    return results

async def classify_questions_batch_ai(question_texts: List[str], available_skills: List[str]) -> Dict[str, List[str]]:
    """Use the configured AI model to classify multiple questions at once for efficiency."""
    # Prepare numbered list of questions
    questions_formatted = "\n".join([f"{i}. {text[:500]}" for i, text in enumerate(question_texts)])
        
    prompt = f"""
    Map each of the following {len(question_texts)} questions to 1-3 most relevant skills from the provided list.
        
    Available Skills: {', '.join(available_skills)}
        
    Questions:
    {questions_formatted}
        
    Return ONLY a valid JSON object where the keys are the question numbers (as strings "0", "1", etc.) and values are arrays of skill names.
    Example:
    {{
        "0": ["Skill A", "Skill B"],
        "1": ["Skill C"]
    }}
    """

    response = await client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert at mapping educational content to learning skills. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content.strip()
    # Pull the JSON object out in case the model wraps it in a code fence or extra text
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    batch_results = json.loads(json_match.group() if json_match else content)
        
    # Clean and validate
    cleaned_results = {}
    for key, skills in batch_results.items():
        if isinstance(skills, list):
            valid_skills = [s for s in skills if s in available_skills]
            cleaned_results[key] = valid_skills[:3]
        
    return cleaned_results
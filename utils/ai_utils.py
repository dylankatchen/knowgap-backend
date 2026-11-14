# Import necessary libraries
from openai import AsyncOpenAI
from config import Config
# Initialize OpenAI client with your API key
client = AsyncOpenAI(api_key=Config.OPENAI_KEY)

# Define the coroutine for generating YouTube search topics for a skill
async def generate_skill_search_topics(skill_name, course_name, course_context="", sample_questions=None):
    """
    Generate 1-3 concise YouTube search phrases for a skill using GPT.

    Parameters:
    - skill_name (str): The name of the skill.
    - course_name (str): The name of the course the skill belongs to.
    - course_context (str): Additional context for the course, provided by the instructor or Canvas syllabus.
    - sample_questions (list[str]): A few example quiz questions that test this skill, for extra context.

    Returns:
    - dict: {"success": True, "topics": [str, ...]} or {"success": False, "error": str}
    """
    prompt = (
        f"A student is struggling with the skill \"{skill_name}\" in the course {course_name}. "
        f"Generate 1 to 3 short, specific YouTube search phrases (each no longer than 6 words) "
        f"that would find helpful educational videos teaching this skill at a college/university level. "
        f"Return only the phrases, one per line, with no numbering or extra commentary."
    )

    if course_context:
        prompt += f"\nHere's relevant course context: {course_context}"

    if sample_questions:
        joined_questions = " | ".join(sample_questions[:3])
        prompt += f"\nHere are example quiz questions that test this skill: {joined_questions}"

    messages = [{"role": "user", "content": prompt}]

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=10000,
            top_p=0.5
        )

        raw_text = response.choices[0].message.content.strip()
        topics = [
            line.strip().strip('"').strip("'").lstrip('-*0123456789. ').strip()
            for line in raw_text.splitlines()
            if line.strip()
        ]
        topics = [t for t in topics if t][:3]

        if not topics:
            return {"success": False, "error": "No topics generated"}

        return {"success": True, "topics": topics}

    except Exception as e:
        print(f"Error generating skill search topics: {e}")
        return {"success": False, "error": str(e)}

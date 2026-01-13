# services/achieveup_ai_service.py

import logging
import json
import re
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
import openai
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Course code to skill category mapping for fallback
COURSE_CODE_MAPPINGS = {
    'COP': ['Programming Fundamentals', 'Algorithm Design', 'Data Structures', 'Object-Oriented Programming', 'Software Development'],
    'CDA': ['Computer Architecture', 'System Design', 'Assembly Language', 'Hardware-Software Interface'],
    'COT': ['Theoretical Computer Science', 'Discrete Mathematics', 'Computational Complexity', 'Algorithm Analysis'],
    'CNT': ['Network Protocols', 'Network Security', 'Network Administration', 'Distributed Systems'],
    'CIS': ['Information Systems', 'Database Management', 'System Analysis', 'IT Project Management'],
    'CGS': ['Computer Applications', 'Digital Literacy', 'Information Technology', 'Computer Skills'],
    'CAP': ['Software Engineering', 'Software Architecture', 'Software Testing', 'Project Management'],
    'CEN': ['Software Engineering', 'System Integration', 'Requirements Analysis', 'Software Design']
}

GENERIC_SKILLS = [
    'Critical Thinking', 'Problem Solving', 'Analytical Reasoning', 'Communication',
    'Research Skills', 'Time Management', 'Collaboration', 'Technical Writing'
]

async def suggest_skills_for_course(course_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate AI-powered skill suggestions for a course.
    
    Args:
        course_data: Dictionary containing courseId, courseName, courseCode, courseDescription
    
    Returns:
        List of skill suggestions with relevance scores
    """
    try:
        # Primary: AI-based skill generation
        ai_skills = await generate_ai_skill_suggestions(course_data)
        if ai_skills:
            logger.info(f"Generated {len(ai_skills)} AI skills for course {course_data.get('courseId')}")
            return ai_skills
    except Exception as e:
        logger.error(f"AI skill generation failed: {str(e)}")
    
    # Fallback: Rule-based skill generation
    logger.info("Using fallback rule-based skill generation")
    return generate_fallback_skills(course_data)

async def generate_ai_skill_suggestions(course_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate skill suggestions using OpenAI."""
    if not openai.api_key:
        logger.warning("OpenAI API key not configured")
        return None
    
    try:
        course_name = course_data.get('courseName', '')
        course_code = course_data.get('courseCode', '')
        course_description = course_data.get('courseDescription', 'N/A')
        
        prompt = f"""
        Analyze this course and suggest 10-12 specific, measurable skills that students should develop. 
        Focus on technical and practical skills relevant to the course content.
        
        Course: {course_name}
        Code: {course_code}
        Description: {course_description}
        
        Return ONLY a valid JSON array with this exact format:
        [
            {{"skill": "Specific Skill Name", "relevance": 0.95, "description": "Brief description of the skill"}},
            {{"skill": "Another Skill", "relevance": 0.90, "description": "Another description"}}
        ]
        
        Guidelines:
        - Skills should be specific and measurable
        - Relevance scores between 0.7 and 1.0
        - Focus on practical, applicable skills
        - Avoid generic skills like "communication" or "teamwork"
        - Make skills relevant to the course subject matter
        """
        

        client=AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            message=[
                {"role": "system", "content": "You are an expert curriculum designer who creates specific, measurable learning outcomes."},
                {"role": "user", "content": prompt}
            ],
            #temperature = 0.3,
            max_completion_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            skills_data = json.loads(json_match.group())
            
            # Validate and normalize skills
            validated_skills = []
            for skill in skills_data[:12]:  # Limit to 12 skills
                if isinstance(skill, dict) and 'skill' in skill:
                    validated_skills.append({
                        'skill': skill['skill'],
                        'relevance': min(max(skill.get('relevance', 0.8), 0.7), 1.0),
                        'description': skill.get('description', 'Relevant skill for this course')
                    })
            
            return validated_skills if len(validated_skills) >= 6 else None
        
        return None
        
    except Exception as e:
        logger.error(f"OpenAI skill generation error: {str(e)}")
        return None

def generate_fallback_skills(course_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate skills using rule-based fallback logic."""
    course_code = course_data.get('courseCode', '').upper()
    course_name = course_data.get('courseName', '').lower()
    
    # Extract course prefix (e.g., COP from COP3530)
    course_prefix = re.match(r'^([A-Z]+)', course_code)
    prefix = course_prefix.group(1) if course_prefix else None
    
    skills = []
    
    # Use course code mapping
    if prefix and prefix in COURSE_CODE_MAPPINGS:
        base_skills = COURSE_CODE_MAPPINGS[prefix]
        for i, skill in enumerate(base_skills):
            skills.append({
                'skill': skill,
                'relevance': 0.9 - (i * 0.05),  # Decreasing relevance
                'description': f"Core {prefix} skill relevant to {course_data.get('courseName', 'this course')}"
            })
    
    # Add course-specific skills based on name analysis
    if 'web' in course_name or 'html' in course_name:
        skills.extend([
            {'skill': 'HTML/CSS Fundamentals', 'relevance': 0.95, 'description': 'Core web markup and styling'},
            {'skill': 'JavaScript Programming', 'relevance': 0.90, 'description': 'Client-side scripting'},
            {'skill': 'Responsive Design', 'relevance': 0.85, 'description': 'Mobile-first design principles'}
        ])
    elif 'database' in course_name or 'sql' in course_name:
        skills.extend([
            {'skill': 'SQL Query Writing', 'relevance': 0.95, 'description': 'Database query and manipulation'},
            {'skill': 'Database Design', 'relevance': 0.90, 'description': 'Relational database modeling'},
            {'skill': 'Data Normalization', 'relevance': 0.85, 'description': 'Database optimization techniques'}
        ])
    elif 'network' in course_name:
        skills.extend([
            {'skill': 'Network Protocols', 'relevance': 0.95, 'description': 'TCP/IP and network communication'},
            {'skill': 'Network Security', 'relevance': 0.90, 'description': 'Network protection and authentication'},
            {'skill': 'Network Troubleshooting', 'relevance': 0.85, 'description': 'Network diagnostics and repair'}
        ])
    
    # Ensure we have at least 8 skills
    while len(skills) < 8:
        remaining_generic = [skill for skill in GENERIC_SKILLS if skill not in [s['skill'] for s in skills]]
        if remaining_generic:
            skills.append({
                'skill': remaining_generic[0],
                'relevance': 0.75,
                'description': f"General academic skill applicable to {course_data.get('courseName', 'this course')}"
            })
        else:
            break
    
    return skills[:12]  # Limit to 12 skills

async def analyze_questions(questions_data: List[Dict[str, Any]], course_skills: List[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze questions for complexity and skill mapping.
    
    Args:
        questions_data: List of question objects with id, text, type, points
        course_skills: Available skills for the course
    
    Returns:
        List of question analysis results
    """
    results = []
    
    for question in questions_data:
        try:
            # Analyze complexity
            complexity = analyze_question_complexity(question)
            
            # Map to skills
            suggested_skills = await map_question_to_skills(question, course_skills)
            
            # Calculate confidence
            confidence = calculate_confidence_score(question, suggested_skills)
            
            results.append({
                'questionId': question.get('id'),
                'complexity': complexity,
                'suggestedSkills': suggested_skills,
                'confidence': confidence,
                'analysis_timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Question analysis error for question {question.get('id')}: {str(e)}")
            results.append({
                'questionId': question.get('id'),
                'complexity': 'medium',
                'suggestedSkills': [],
                'confidence': 0.5,
                'error': str(e)
            })
    
    return results

def analyze_question_complexity(question: Dict[str, Any]) -> str:
    """Analyze question complexity based on text content and structure."""
    question_text = question.get('question_text', '') or question.get('text', '')
    points = question.get('points', 1)
    
    # Text-based indicators
    text_length = len(question_text)
    word_count = len(question_text.split())
    
    # Complexity indicators
    high_complexity_words = [
        'analyze', 'evaluate', 'compare', 'contrast', 'synthesize', 'justify', 'critique',
        'design', 'implement', 'optimize', 'debug', 'troubleshoot', 'architect'
    ]
    
    medium_complexity_words = [
        'explain', 'describe', 'apply', 'demonstrate', 'solve', 'calculate',
        'identify', 'classify', 'interpret', 'predict'
    ]
    
    low_complexity_words = [
        'define', 'list', 'name', 'recall', 'state', 'recognize', 'select', 'choose'
    ]
    
    question_lower = question_text.lower()
    
    # Count complexity indicators
    high_count = sum(1 for word in high_complexity_words if word in question_lower)
    medium_count = sum(1 for word in medium_complexity_words if word in question_lower)
    low_count = sum(1 for word in low_complexity_words if word in question_lower)
    
    # Scoring system
    complexity_score = 0
    
    # Text length and word count
    if word_count > 50:
        complexity_score += 2
    elif word_count > 25:
        complexity_score += 1
    
    # Points value
    if points >= 10:
        complexity_score += 2
    elif points >= 5:
        complexity_score += 1
    
    # Keyword analysis
    complexity_score += high_count * 3
    complexity_score += medium_count * 2
    complexity_score -= low_count * 1
    
    # Question type analysis
    if any(phrase in question_lower for phrase in ['multiple choice', 'select all', 'true/false']):
        complexity_score -= 1
    elif any(phrase in question_lower for phrase in ['essay', 'explain', 'describe in detail']):
        complexity_score += 2
    
    # Final classification
    if complexity_score >= 6:
        return 'high'
    elif complexity_score >= 3:
        return 'medium'
    else:
        return 'low'

async def map_question_to_skills(question: Dict[str, Any], available_skills: List[str] = None) -> List[str]:
    """Map a question to relevant skills using AI or keyword matching."""
    question_text = question.get('question_text', '') or question.get('text', '')
    
    if not available_skills:
        available_skills = GENERIC_SKILLS
    
    suggested_skills = []
    
    try:
        # Try AI-based classification first
        if openai.api_key:
            ai_skills = await classify_question_skills_ai(question_text, available_skills)
            if ai_skills:
                suggested_skills = ai_skills
    except Exception as e:
        logger.error(f"AI skill classification failed: {str(e)}")
    
    # If AI didn't return skills, fallback to keyword-based matching
    if not suggested_skills:
        suggested_skills = classify_question_skills_keywords(question_text, available_skills)
    
    # Final safety net: If still no skills, ensure at least one suggestion
    if not suggested_skills and available_skills:
        # Use intelligent fallback based on question content and type
        suggested_skills = get_fallback_skill_suggestion(question, available_skills)
    
    # Absolute last resort: return the first available skill
    if not suggested_skills and available_skills:
        suggested_skills = [available_skills[0]]
    
    return suggested_skills

async def classify_question_skills_ai(question_text: str, available_skills: List[str]) -> List[str]:
    """Use OpenAI to classify question skills."""
    if not openai.api_key or len(available_skills) == 0:
        return None
    
    try:
        prompt = f"""
        Given this question and list of available skills, identify which skills (1-3) are most relevant to answering this question.
        
        Question: {question_text}
        
        Available Skills: {', '.join(available_skills)}
        
        Return ONLY a JSON array of the most relevant skill names (maximum 3):
        ["Skill Name 1", "Skill Name 2", "Skill Name 3"]
        
        Only include skills that are directly relevant to the question content.
        """

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert at mapping educational content to learning skills."},
                {"role": "user", "content": prompt}
            ],
            #temperature=0.1,
            max_completion_tokens=10000
        )

        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON array
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            skills = json.loads(json_match.group())
            
            # Validate skills are in available list
            valid_skills = [skill for skill in skills if skill in available_skills]
            return valid_skills[:3]  # Maximum 3 skills
        
        return None
        
    except Exception as e:
        logger.error(f"AI skill classification error: {str(e)}")
        return None

def get_fallback_skill_suggestion(question: Dict[str, Any], available_skills: List[str]) -> List[str]:
    """Provide intelligent fallback skill suggestion when other methods fail."""
    question_text = (question.get('question_text', '') or question.get('text', '')).lower()
    question_type = question.get('type', '').lower()
    
    # Question type-based suggestions
    if 'multiple_choice' in question_type:
        # Multiple choice often tests fundamental concepts
        for skill in available_skills:
            if 'fundamental' in skill.lower() or 'basic' in skill.lower():
                return [skill]
    
    elif 'essay' in question_type or 'short_answer' in question_type:
        # Essay/short answer often requires applied knowledge
        for skill in available_skills:
            if any(word in skill.lower() for word in ['programming', 'design', 'development', 'analysis']):
                return [skill]
    
    elif 'coding' in question_type or 'file_upload' in question_type:
        # Coding questions likely programming-related
        for skill in available_skills:
            if 'programming' in skill.lower() or 'coding' in skill.lower():
                return [skill]
    
    # Content-based broad matching (more aggressive than keyword matching)
    content_skill_mapping = {
        # Web Development indicators
        ['web', 'html', 'css', 'javascript', 'js', 'dom', 'element', 'tag', 'style', 'layout', 'responsive', 'grid', 'flexbox', 'browser', 'client']: 
            ['HTML/CSS Fundamentals', 'JavaScript Programming', 'Web APIs', 'DOM Manipulation', 'Responsive Design'],
        
        # Database indicators  
        ['database', 'sql', 'table', 'query', 'select', 'insert', 'update', 'delete', 'join', 'index', 'schema', 'normal']:
            ['SQL Fundamentals', 'Database Design', 'Data Normalization', 'Query Optimization'],
        
        # Network indicators
        ['network', 'tcp', 'ip', 'protocol', 'router', 'switch', 'packet', 'lan', 'wan', 'wifi', 'ethernet', 'security', 'firewall']:
            ['Network Protocols (TCP/IP)', 'Network Security', 'Routing & Switching', 'Wireless Networks', 'Network Troubleshooting'],
        
        # Programming indicators
        ['program', 'code', 'function', 'variable', 'loop', 'array', 'object', 'class', 'method', 'algorithm', 'data structure']:
            ['JavaScript Programming', 'Programming Fundamentals', 'Object-Oriented Programming'],
        
        # General technical indicators
        ['technical', 'system', 'software', 'application', 'development', 'engineering', 'computer']:
            ['Technical Skills', 'System Analysis', 'Software Development']
    }
    
    # Check content against broader patterns
    for keywords, potential_skills in content_skill_mapping.items():
        if any(keyword in question_text for keyword in keywords):
            # Return the first matching skill that's actually available
            for skill in potential_skills:
                if skill in available_skills:
                    return [skill]
            # If no exact match, try partial matching
            for skill in potential_skills:
                for available_skill in available_skills:
                    if any(word in available_skill.lower() for word in skill.lower().split()):
                        return [available_skill]
    
    # Course-specific fallback based on available skills pattern
    skill_priorities = {
        # Web Development course priority
        'web_dev': ['HTML/CSS Fundamentals', 'JavaScript Programming', 'DOM Manipulation', 'Responsive Design', 'Web APIs'],
        # Database course priority  
        'database': ['SQL Fundamentals', 'Database Design', 'Data Normalization', 'Query Optimization', 'Stored Procedures'],
        # Network course priority
        'network': ['Network Protocols (TCP/IP)', 'Network Security', 'Routing & Switching', 'Wireless Networks', 'Network Troubleshooting']
    }
    
    # Detect course type from available skills and return priority skill
    available_lower = [skill.lower() for skill in available_skills]
    
    if any('html' in skill or 'css' in skill or 'javascript' in skill for skill in available_lower):
        for priority_skill in skill_priorities['web_dev']:
            if priority_skill in available_skills:
                return [priority_skill]
    
    elif any('sql' in skill or 'database' in skill for skill in available_lower):
        for priority_skill in skill_priorities['database']:
            if priority_skill in available_skills:
                return [priority_skill]
    
    elif any('network' in skill or 'tcp' in skill for skill in available_lower):
        for priority_skill in skill_priorities['network']:
            if priority_skill in available_skills:
                return [priority_skill]
    
    # Final fallback: return the most "fundamental" sounding skill
    for skill in available_skills:
        if any(word in skill.lower() for word in ['fundamental', 'basic', 'programming', 'development']):
            return [skill]
    
    # Ultimate fallback: return first skill (this should never be reached due to earlier check)
    return [available_skills[0]] if available_skills else []


def classify_question_skills_keywords(question_text: str, available_skills: List[str]) -> List[str]:
    """Classify question skills using keyword matching."""
    question_lower = question_text.lower()
    skill_scores = {}
    
    for skill in available_skills:
        score = 0
        skill_lower = skill.lower()
        skill_words = skill_lower.split()
        
        # Direct skill name match
        if skill_lower in question_lower:
            score += 10
        
        # Individual word matches
        for word in skill_words:
            if len(word) > 3 and word in question_lower:
                score += 3
        
        # Related keyword matching
        skill_keywords = get_skill_keywords(skill)
        for keyword in skill_keywords:
            if keyword in question_lower:
                score += 2
        
        if score > 0:
            skill_scores[skill] = score
    
    # Return top 3 skills by score
    sorted_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    top_skills = [skill for skill, score in sorted_skills[:3]]
    
    # Ensure at least one skill is returned
    if not top_skills and available_skills:
        # If no keyword matches found, return the first available skill as fallback
        top_skills = [available_skills[0]]
    
    return top_skills

def get_skill_keywords(skill: str) -> List[str]:
    """Get related keywords for a skill."""
    skill_keyword_map = {
        'Programming Fundamentals': ['code', 'program', 'algorithm', 'function', 'variable', 'loop'],
        'HTML/CSS Fundamentals': ['html', 'css', 'web', 'tag', 'style', 'markup'],
        'JavaScript Programming': ['javascript', 'js', 'script', 'dom', 'event', 'function'],
        'Database Management': ['database', 'sql', 'query', 'table', 'data', 'select'],
        'Network Protocols': ['network', 'protocol', 'tcp', 'ip', 'http', 'packet'],
        'Software Testing': ['test', 'testing', 'debug', 'error', 'bug', 'validation'],
        'Algorithm Design': ['algorithm', 'efficiency', 'complexity', 'optimization', 'sort', 'search'],
        'Data Structures': ['array', 'list', 'tree', 'graph', 'stack', 'queue', 'hash'],
        'Object-Oriented Programming': ['class', 'object', 'inheritance', 'polymorphism', 'encapsulation'],
        'Problem Solving': ['solve', 'solution', 'approach', 'strategy', 'analyze', 'reasoning']
    }
    
    return skill_keyword_map.get(skill, [])

def calculate_confidence_score(question: Dict[str, Any], suggested_skills: List[str]) -> float:
    """Calculate confidence score for skill suggestions."""
    question_text = question.get('question_text', '') or question.get('text', '')
    
    base_confidence = 0.7
    
    # Number of skills suggested
    if len(suggested_skills) == 0:
        return 0.3
    elif len(suggested_skills) == 1:
        base_confidence += 0.1
    elif len(suggested_skills) <= 3:
        base_confidence += 0.05
    
    # Question length (more text = better analysis)
    text_length = len(question_text)
    if text_length > 200:
        base_confidence += 0.1
    elif text_length > 100:
        base_confidence += 0.05
    
    # Technical terminology density
    technical_words = ['algorithm', 'function', 'database', 'network', 'protocol', 'class', 'object', 'array']
    technical_count = sum(1 for word in technical_words if word in question_text.lower())
    if technical_count > 0:
        base_confidence += min(technical_count * 0.02, 0.1)
    
    return min(base_confidence, 1.0)

async def bulk_assign_skills(course_id: str, quiz_id: str, questions: List[Dict[str, Any]], course_skills: List[str]) -> Dict[str, List[str]]:
    """Perform bulk skill assignment for all questions in a quiz."""
    try:
        assignments = {}
        
        # Analyze all questions
        question_analyses = await analyze_questions(questions, course_skills)
        
        # Extract skill assignments
        for analysis in question_analyses:
            question_id = analysis.get('questionId')
            suggested_skills = analysis.get('suggestedSkills', [])
            
            # Only assign skills with reasonable confidence
            if analysis.get('confidence', 0) >= 0.5 and suggested_skills:
                assignments[question_id] = suggested_skills
            else:
                assignments[question_id] = []
        
        logger.info(f"Bulk assigned skills to {len(assignments)} questions in quiz {quiz_id}")
        return assignments
        
    except Exception as e:
        logger.error(f"Bulk skill assignment error: {str(e)}")
        return {} 
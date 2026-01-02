import os
import json
from groq import Groq

class CoursePlanner:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = None
            print("Warning: CoursePlanner initialized without GROQ_API_KEY")

    async def generate_outline(self, scraped_data_path):
        if not self.client:
            raise ValueError("GROQ_API_KEY is missing. Please set it in the .env file.")

        if not os.path.exists(scraped_data_path):
            raise FileNotFoundError(f"Scraped data not found at {scraped_data_path}")

        with open(scraped_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        title = data.get("title", "Untitled Course")
        text_content = data.get("text_content", "")[:15000] # Groq Llama 3 has good context

        prompt = f"""
        You are an expert curriculum designer. 
        Create a structured training course based on the following website content.
        
        Website Title: {title}
        Content Snippet: {text_content}...

        Output a JSON structure with the following schema:
        {{
            "course_title": "String",
            "description": "String",
            "modules": [
                {{
                    "title": "String",
                    "lessons": [
                        {{
                            "title": "String",
                            "description": "Brief summary of what this lesson covers"
                        }}
                    ]
                }}
            ]
        }}
        """

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Updated to current model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates JSON curriculum. Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        plan = json.loads(response.choices[0].message.content)
        return plan

    async def generate_lesson(self, lesson_title: str, context: str):
        if not self.client:
             # Return mock content if no key
            return f"# {lesson_title}\n\n*Mock Content (No API Key)*\n\nThis is a placeholder for **{lesson_title}**."

        prompt = f"""
        You are an expert technical instructor.
        Write a comprehensive, engaging lesson for the topic: "{lesson_title}".
        
        Use the following background context from the website:
        {context[:8000]}

        CRITICAL FORMATTING REQUIREMENTS:
        - EVERY sentence MUST end with proper punctuation (. ! or ?)
        - Write in complete, grammatically correct sentences
        - Use markdown formatting for headers (##), bold (**text**), and lists
        
        Format the output in clean Markdown.
        Include:
        - A clear introduction
        - Step-by-step concepts or instructions
        - Code snippets if relevant (use ```blocks)
        - A "Key Takeaways" summary at the end.
        
        Do NOT output JSON. Output pure Markdown with proper punctuation.
        """

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful technical writer who always uses proper punctuation."},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content
        
        # Post-process to ensure proper punctuation
        content = self._ensure_proper_punctuation(content)
        
        return content
    
    def _ensure_proper_punctuation(self, text):
        """Ensure all sentences end with proper punctuation."""
        import re
        
        # Split into lines to preserve markdown structure
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Skip empty lines and markdown headers
            if not line.strip() or line.strip().startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Skip lines that are list items
            if re.match(r'^\s*[-*+]\s', line) or re.match(r'^\s*\d+\.\s', line):
                # For list items, ensure they end with punctuation
                line = line.rstrip()
                if line and not re.search(r'[.!?:)]$', line):
                    line += '.'
                fixed_lines.append(line)
                continue
            
            # For regular text lines, ensure they end with punctuation
            line = line.rstrip()
            if line and not re.search(r'[.!?]$', line):
                # Don't add period if line ends with a colon (might be before a list)
                if not line.endswith(':'):
                    line += '.'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    async def generate_quiz(self, lesson_content: str):
        if not self.client:
            # Mock quiz
            return [
                {
                    "question": "What is the main topic? (Mock)",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 0
                }
            ]

        prompt = f"""
        create a short quiz based on the following lesson content:
        {lesson_content[:4000]}

        Output a JSON OBJECT with a key "questions" containing an array of 3 objects:
        {{
            "questions": [
                {{
                    "question": "String",
                    "options": ["String", "String", "String", "String"],
                    "correct_index": Integer (0-3)
                }}
            ]
        }}
        """

        print(f"Generating quiz for content length: {len(lesson_content)}")

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        print(f"Quiz Raw Response: {raw_content[:200]}...") # Log start of response

        try:
             result = json.loads(raw_content)
             if "questions" in result:
                 return result["questions"]
             # If it returned a list wrapped in nothing (rare with json_object mode but possible if model ignores system)
             if isinstance(result, list):
                 return result
             
             print("Parsed JSON but found no questions list.")
             return []
        except Exception as e:
             print(f"JSON Parse Error: {e}")
             return []

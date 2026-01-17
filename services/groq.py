# services/groq.py
import httpx
import json
import re
from config import GROQ_API_KEY


async def format_text_with_groq(text: str) -> dict:
    """Send text to Groq LLM to generate title and format body with selective highlights"""
    if not text:
        return {"title": "", "body": text}
    
    if not GROQ_API_KEY:
        print("[GROQ] API key not found!")
        return {"title": "", "body": text}
    
    print(f"[GROQ] Processing: {text[:50]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are an expert social media copywriter. Your task is to format text for viral reels/shorts.

Given input text, you must return a JSON object with:
1. "title": A short, catchy headline (5-10 words max) that captures the essence. Make it punchy and attention-grabbing.
2. "body": The main text with ONLY 2-4 of the most impactful words/phrases wrapped in **bold**. 

Rules for highlighting:
- Only highlight action words, key benefits, or emotional triggers
- Never highlight common words like "and", "the", "for", "to", "a"
- Don't over-highlight - less is more
- Keep the original message intact

Return ONLY valid JSON, no explanation.

Example input: "Learn how to make passive income online with our proven strategies for beginners"
Example output: {"title": "Passive Income Made Simple", "body": "Learn how to make **passive income** online with our **proven strategies** for beginners"}"""
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.4,
                    "max_tokens": 600
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["choices"][0]["message"]["content"].strip()
                
                # Parse JSON response
                try:
                    # Clean up response if needed
                    result = result.replace('```json', '').replace('```', '').strip()
                    parsed = json.loads(result)
                    print(f"[GROQ] Success! Title: {parsed.get('title', '')[:30]}...")
                    return parsed
                except json.JSONDecodeError:
                    # Fallback - extract what we can
                    print(f"[GROQ] JSON parse failed, using fallback")
                    return {"title": "", "body": result}
            else:
                print(f"[GROQ] Error {response.status_code}")
                return {"title": "", "body": text}
    except Exception as e:
        print(f"[GROQ] Exception: {e}")
        return {"title": "", "body": text}

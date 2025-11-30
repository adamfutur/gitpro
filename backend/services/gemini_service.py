import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

def call_gemini(prompt, context=''):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Failed to get AI response."

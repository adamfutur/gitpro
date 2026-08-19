import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

def call_gemini(prompt, context=''):
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Failed to get AI response."


def call_gemini_with_tools(prompt, tools, context=''):
    """
    Sends a prompt to Gemini along with a set of Python functions as callable
    tools. Gemini decides which tools (if any) it needs to call to answer the
    question, instead of every possible piece of context being fetched and
    stuffed into the prompt up front.
    """
    try:
        model = genai.GenerativeModel('gemini-flash-latest', tools=tools)
        chat = model.start_chat(enable_automatic_function_calling=True)
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        response = chat.send_message(full_prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Failed to get AI response."

import google.generativeai as genai
import os

def process_text(input_text, mode="speed", task_type="summary", api_key=None, num_questions=5, difficulty="Medium"):
    active_key = api_key or os.environ.get("GEMINI_API_KEY")

    if not active_key:
        return "Error: No API Key provided. Please enter it manually or set the GEMINI_API_KEY environment variable."
    
    active_key = active_key.strip()

    try:
        genai.configure(api_key=active_key)
        
        if mode == "speed":
            target_model = "gemini-2.5-flash"
        else:
            target_model = "gemini-2.5-pro"
        
        if task_type == "mcq":
            prompt = f"""
            Generate {num_questions} multiple-choice questions (MCQs) based strictly on the text provided below.
            Difficulty Level: {difficulty}.
            
            Format each question clearly with:
            1. The Question
            2. 4 Options (labeled A, B, C, D)
            3. The Correct Answer (clearly indicated at the end)
            
            TEXT:
            {input_text}
            """
        else:
            prompt = f"""
            Summarize the following text comprehensively. Capture the main points and key details.
            
            TEXT:
            {input_text}
            """
        # ------------------------

        try:
            model = genai.GenerativeModel(target_model)
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as first_error:
            # Fallback logic
            fallback_model = "gemini-2.0-flash"
            model = genai.GenerativeModel(fallback_model)
            response = model.generate_content(prompt)
            return f"{response.text}\n\n(Note: Generated using fallback model '{fallback_model}')"

    except Exception as e:
        return f"API Error: {str(e)}"
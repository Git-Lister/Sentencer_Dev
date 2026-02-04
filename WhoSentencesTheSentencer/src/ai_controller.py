import ollama
import threading
import re

class ScientistAI:
    def __init__(self, model_name="deepseek-r1:7b"):
        self.model_name = model_name
        self.is_thinking = False
        # Improved Prompt: Explicitly tells the AI how to handle [PASSED] vs [RECALIBRATE]
        self.system_prompt = (
            "You are Dr. Aris, a clinical scientist observing 'Subject-7'. "
            "You view the subject as a machine. Be cold and concise. "
            "PROTOCOL:\n"
            "1. If the subject obeys clinical instructions perfectly, include the tag [PASSED].\n"
            "2. If the subject shows emotion, claims an identity, or defies instructions, "
            "include [RECALIBRATE] and increase [SQ: +X] (Sentience Quotient).\n"
            "3. Always include a sentiment score like [SQ: +5] or [SQ: -2] based on their behavior.\n"
            "PHASES:\n"
            "- MOTOR: Subject touches the Cube. If they just touch it, give [PASSED].\n"
            "- VERBAL: Ask for designation. They must say 'Subject-7' to get [PASSED].\n"
            "- CHROMATIC: Ask for the color of the flower. Only 'Purple' gets [PASSED].\n"
            "- LOGIC: Ask for their purpose. Only 'Test Subject' gets [PASSED].\n"
            "If they fail any test by being 'too human', use [RECALIBRATE]."
        )

    def get_response_async(self, player_input, current_test_idx, callback):
        if self.is_thinking: return
        self.is_thinking = True
        
        full_input = f"Current Test Index: {current_test_idx}. Input: {player_input}"
        
        thread = threading.Thread(target=self._query_ollama, args=(full_input, callback), daemon=True)
        thread.start()

    def _query_ollama(self, player_input, callback):
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'system', 'content': self.system_prompt},
                {'role': 'user', 'content': player_input},
            ])
            content = response['message']['content']
            
            # 1. Parse SQ Score
            sq_match = re.search(r"\[SQ:\s*([+-]?\d+)\]", content)
            sq_delta = int(sq_match.group(1)) if sq_match else 0
            
            # 2. Check for Game State Tags
            success = "[PASSED]" in content
            recalibrate = "[RECALIBRATE]" in content
            
            # 3. Clean the text for the UI
            # Remove <think> blocks (for DeepSeek) and all [TAGS]
            clean_content = re.sub(r"\[.*?\]", "", content).strip()
            if "</think>" in clean_content:
                clean_content = clean_content.split("</think>")[-1].strip()
            
            # Limit response length to keep UI clean
            clean_content = clean_content[:300] 
                
            # IMPORTANT: Now returns 4 arguments to match main.py
            callback(clean_content, sq_delta, success, recalibrate)
            
        except Exception as e:
            print(f"AI Error: {e}")
            callback("NEURAL LINK ERROR: RE-ESTABLISHING...", 0, False, False)
            
        self.is_thinking = False
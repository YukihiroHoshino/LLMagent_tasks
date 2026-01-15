# src/llm_client.py
import os
import json
import re
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

load_dotenv()

# Google API Keyの設定
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_llm_response(system_prompt: str, user_prompt: str, model: str = "gemini-2.5-flash-preview-09-2025", temperature: float = 0.7) -> dict:
    """
    Geminiに問い合わせを行い、JSONとしてパースした結果を返す。
    temperatureはデフォルトで0.7（ランダム性あり）に設定。
    """
    try:
        # System promptの設定
        # Geminiではsystem instructionとしてモデル初期化時に渡すのが一般的です
        # JSON出力を強制するために明示的に指示も含めます
        full_system_instruction = f"{system_prompt}\nOutput JSON only."
        
        generative_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=full_system_instruction
        )

        # 設定: JSONモードを有効化
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            temperature=temperature
        )

        response = generative_model.generate_content(
            user_prompt,
            generation_config=generation_config
        )
        
        content = response.text
        return parse_json(content)
        
    except Exception as e:
        print(f"LLM API Error: {e}")
        # エラーの内容によっては詳細をログに出すなど調整してください
        return {
            "thought_process": "Error occurred during API call",
            "message": "...",
            "ACTION": "[TALK]",
            "error_details": str(e)
        }

def parse_json(content: str) -> dict:
    """
    Markdownのコードブロックなどを除去してJSONをパースする
    GeminiのJSONモードはクリーンなJSONを返しますが、念のためクリーニング処理を残します。
    """
    try:
        # ```json ... ``` の除去
        json_str = re.sub(r"^```json\s*", "", content)
        json_str = re.sub(r"\s*```$", "", json_str)
        # 余分な空白のトリム
        json_str = json_str.strip()
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"JSON Parse Error. Content: {content}")
        return {"ACTION": "[TALK]", "message": "Error parsing response."}
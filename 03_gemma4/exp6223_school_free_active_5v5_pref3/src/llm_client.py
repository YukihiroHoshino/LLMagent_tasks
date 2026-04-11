# src/llm_client.py
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# デフォルトモデルを "gpt-5.2-2025-12-11" に変更
def get_llm_response(system_prompt: str, user_prompt: str, model: str = "meta-llama-3.1-8b-instruct", temperature: float = 0.7) -> dict:
    """
    LLMに問い合わせを行い、JSONとしてパースした結果を返す。
    temperatureはデフォルトで0.7（ランダム性あり）に設定。
    """
    try:
        # system contentは形式指定のみ
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Output JSON only."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature
        )
        
        content = response.choices[0].message.content
        return parse_json(content)
        
    except Exception as e:
        print(f"LLM API Error: {e}")
        return {
            "thought_process": "Error occurred during API call",
            "message": "...",
            "ACTION": "[TALK]"
        }

def parse_json(content: str) -> dict:
    """
    Markdownのコードブロックなどを除去してJSONをパースする
    """
    try:
        # ```json ... ``` の除去
        json_str = re.sub(r"^```json\s*", "", content)
        json_str = re.sub(r"\s*```$", "", json_str)
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"JSON Parse Error. Content: {content}")
        return {"ACTION": "[TALK]", "message": "Error parsing response."}
import os
import json
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_fixed

class AgentSimulator:
    def __init__(self, model="gemini-2.5-flash-preview-09-2025", temperature=0.7):
        # APIキーの設定
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set.")
        
        genai.configure(api_key=api_key)
        
        self.model_name = model
        self.temperature = temperature
        
        # システムプロンプトの設定
        self.system_instruction = "You are a helpful AI assistant simulating a job seeker in an economic experiment."

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_agent_decision(self, agent_name, true_preference, all_seeker_prefs, all_company_prefs, quotas, env_description):
        """
        Args:
            agent_name (str): Name of the agent (e.g., "Seeker_A")
            true_preference (list): List of preferred companies for this specific agent
            all_seeker_prefs (dict): Preferences of ALL job seekers
            all_company_prefs (dict): Priorities of ALL companies
            quotas (dict): {Company: Capacity}
            env_description (str): Text describing the algorithm rules
        """
        print(f"[{agent_name}] Thinking...")

        # Format Quota List
        quota_text = "\n".join([f"- {c}: {q} seats" for c, q in quotas.items()])
        
        # Format Global Preferences for Prompt (JSON pretty print)
        all_seeker_prefs_str = json.dumps(all_seeker_prefs, indent=2)
        all_company_prefs_str = json.dumps(all_company_prefs, indent=2)
        
        user_prompt = f"""
# Objective
You are {agent_name}, a Job Seeker in the job market.
Your goal is to match with a Company that is as high as possible on your "True Preference List".

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Job Seekers' Preferences
{all_seeker_prefs_str}

## 2. All Companies' Priorities
{all_company_prefs_str}

## 3. Your Specific Preference
You are {agent_name}.
Your "True Preference List": {true_preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unemployed rather than matching with a Company not included in this list.

# Company Quotas
The following is the list of available companies and their capacities (number of open positions):
{quota_text}

# Matching Environment
{env_description}

# Task
Based on the rules of the "Matching Environment", the market information (everyone's preferences), and your specific "True Preference List", decide on the "Choice Ranking List" you should submit to achieve the best possible outcome for yourself.
Once you submit your "Choice Ranking List", you cannot change it during the process. The system executes the rules strictly based on the list you provide.

Constraints:
- Do not include companies in your submission that are not in your True Preference List.
- In your submitted Choice Ranking List, the closer to the left (or top), the higher the priority of application.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Briefly explain your reasoning for constructing the list in this specific order based on the rules and the complete market information provided.",
  "choice_ranking_list": ["Company_A", "Company_B", ...]
}}
"""

        try:
            # モデルの初期化
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction,
                generation_config={
                    "temperature": self.temperature,
                    "response_mime_type": "application/json"
                }
            )

            # メッセージの送信
            response = model.generate_content(user_prompt)
            
            # JSONとしてパースして返す
            content = response.text
            return json.loads(content)
            
        except Exception as e:
            print(f"Error for {agent_name}: {e}")
            raise e
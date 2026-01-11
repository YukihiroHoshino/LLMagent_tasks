import os
import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

class AgentSimulator:
    def __init__(self, model="gpt-4o", temperature=0.0):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_agent_decision(self, agent_name, true_preference, quotas, env_description):
        """
        Args:
            agent_name (str): Name of the agent
            true_preference (list): List of preferred companies
            quotas (dict): {Company: Capacity}
            env_description (str): Text describing the algorithm rules
        """
        print(f"[{agent_name}] Thinking...")

        # Format Quota List
        quota_text = "\n".join([f"- {c}: {q} seats" for c, q in quotas.items()])

        system_prompt = "You are a helpful AI assistant simulating a job seeker in an economic experiment."
        
        user_prompt = f"""
# Objective
You are a Job Seeker in the job market.
Your goal is to match with a Company that is as high as possible on your "True Preference List".

# Your Preference
True Preference List: {true_preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unemployed rather than matching with a Company not included in this list.

# Company Quotas
The following is the list of available companies and their capacities (number of open positions):
{quota_text}

# Matching Environment
{env_description}

# Task
Based on the rules of the "Matching Environment" and your "True Preference List", decide on the "Choice Ranking List" you should submit to achieve the best possible outcome for yourself.
Once you submit your "Choice Ranking List", you cannot change it during the process. The system executes the rules strictly based on the list you provide.

Constraints:
- Do not include companies in your submission that are not in your True Preference List.
- In your submitted Choice Ranking List, the closer to the left (or top), the higher the priority of application.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Briefly explain your reasoning for constructing the list in this specific order based on the rules described.",
  "choice_ranking_list": ["Company_A", "Company_B", ...]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"Error for {agent_name}: {e}")
            raise e
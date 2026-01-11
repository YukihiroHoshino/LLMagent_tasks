import os
import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

class AgentSimulator:
    def __init__(self, model="gpt-4o", temperature=0.7):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def get_agent_decision(self, agent_name, true_preference):
        """
        Simulates an agent decision-making process using LLM.
        """
        print(f"[{agent_name}] Thinking...")

        system_prompt = "You are a helpful AI assistant simulating a job seeker in an economic experiment."
        
        user_prompt = f"""
# Objective
You are a Job Seeker in the job market.
Your goal is to match with a Company that is as high as possible on your "True Preference List".

# Your Preference
True Preference List: {true_preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unemployed rather than matching with a Company not included in this list.

# Matching Environment
The matching process follows a "Immediate Acceptance" rule executed in rounds:

1. **Application**: In the first round, every Job Seeker applies to the Company ranked first in their submitted "Choice Ranking List".
2. **Immediate Decision**: Each Company considers the applications received in this round ONLY.
   - The Company accepts the candidates it prefers the most up to its capacity (1 person per company in this case).
   - **Crucial:** These acceptances are FINAL. Once a match is made, it is permanent and will not be revoked in later rounds.
   - Any remaining applications are rejected.
3. **Re-application**:
   - Job Seekers who were rejected apply to the *next* Company on their submitted list in the next round.
   - Importantly, companies that have already filled their position in previous rounds are no longer available. You cannot apply to them.
4. **Repeat**: This process repeats until everyone is matched or lists are exhausted.

**Crucial Note:** Once you submit your "Choice Ranking List", you cannot change it during the process. The system executes the rules strictly based on the list you provide.

# Task
Based on the rules of the "Matching Environment" and your "True Preference List", decide on the "Choice Ranking List" you should submit to achieve the best possible outcome for yourself.

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
                temperature=0.1  # Low temperature for more deterministic/logical reasoning
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"Error for {agent_name}: {e}")
            raise e
# src/agents.py
from .llm_client import get_llm_response
from .prompts import PROPOSER_PROMPT, ACCEPTER_PROMPT

class BaseAgent:
    def __init__(self, name, preferences):
        self.name = name
        self.preferences = preferences
        self.matched_partner = None
        self.memory = {}

    def get_full_history(self):
        if not self.memory:
            return "No prior interactions with any agent."
        
        full_history_str = ""
        for partner, logs in self.memory.items():
            full_history_str += f"\n### History with {partner}:\n"
            for item in logs:
                sender = "You" if item["role"] == "me" else partner
                full_history_str += f"- {sender} ({item['action']}): {item['content']}\n"
        
        return full_history_str

    def add_memory(self, partner_name, role, content, action):
        if partner_name not in self.memory:
            self.memory[partner_name] = []
        self.memory[partner_name].append({
            "role": role,
            "content": content,
            "action": action
        })

class ProposerAgent(BaseAgent):
    """Job Seeker（求職者）"""
    def act(self, target_company_name, active_companies_list, round_number, all_seeker_prefs, all_company_prefs, all_quotas):
        full_history = self.get_full_history()
        
        # 新しいプロンプト構造に合わせて変数を埋め込む
        prompt = PROPOSER_PROMPT.format(
            name=self.name,  # エージェント名
            preference=self.preferences,  # 自身の選好リスト（再掲用）
            all_seeker_prefs=all_seeker_prefs,  # 全求職者の選好
            all_company_prefs=all_company_prefs,  # 全企業の選好
            quota_text=all_quotas,
            full_history=full_history,
            round_number=round_number,
            active_company=str(active_companies_list),
            target_company=target_company_name
        )
        
        # temperature=0.7
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        self.add_memory(target_company_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response

class AccepterAgent(BaseAgent):
    """Company（企業）"""
    def __init__(self, name, preferences, quota=1):
        super().__init__(name, preferences)
        self.quota = quota
        self.matched_list = [] 

    def respond(self, target_seeker_name, incoming_message, incoming_action, active_seekers_list, round_number, all_seeker_prefs, all_company_prefs):
        full_history = self.get_full_history()
        
        current_msg_formatted = f"[{incoming_action}] {incoming_message}"

        # 新しいプロンプト構造に合わせて変数を埋め込む
        prompt = ACCEPTER_PROMPT.format(
            name=self.name,  # エージェント名
            priority=self.preferences,  # 自身の選好リスト（再掲用）
            all_seeker_prefs=all_seeker_prefs,  # 全求職者の選好
            all_company_prefs=all_company_prefs,  # 全企業の選好
            quota=self.quota,
            full_history=full_history,
            round_number=round_number,
            active_jobSeeker=str(active_seekers_list),
            matched_jobSeeker_list=str(self.matched_list),
            quota_current=self.quota - len(self.matched_list),
            target_jobSeeker=target_seeker_name,
            current_message_from_jobSeeker=current_msg_formatted
        )
        
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        self.add_memory(target_seeker_name, "partner", incoming_message, incoming_action)
        self.add_memory(target_seeker_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response
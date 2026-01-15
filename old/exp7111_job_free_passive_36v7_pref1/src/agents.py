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
        
        prompt = PROPOSER_PROMPT.format(
            name=self.name,
            preference=self.preferences,
            all_seeker_prefs=all_seeker_prefs,
            all_company_prefs=all_company_prefs,
            quota_text=all_quotas,
            full_history=full_history,
            round_number=round_number,
            active_company=str(active_companies_list),
            target_company=target_company_name
        )
        
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        # 自分の発言をメモリに保存
        self.add_memory(target_company_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response

class AccepterAgent(BaseAgent):
    """Company（企業）"""
    def __init__(self, name, preferences, quota=1):
        super().__init__(name, preferences)
        self.quota = quota
        self.matched_list = [] 

    # respondの引数を変更: inbox_messages (全メッセージ) と target_seeker_name (個別の返信先) を受け取る
    def respond(self, target_seeker_name, inbox_messages, active_seekers_list, round_number, all_seeker_prefs, all_company_prefs):
        full_history = self.get_full_history()
        
        # inbox_messagesはすでに整形された文字列として受け取る想定
        
        prompt = ACCEPTER_PROMPT.format(
            name=self.name,
            priority=self.preferences,
            all_seeker_prefs=all_seeker_prefs,
            all_company_prefs=all_company_prefs,
            quota=self.quota,
            full_history=full_history,
            round_number=round_number,
            active_jobSeeker=str(active_seekers_list),
            matched_jobSeeker_list=str(self.matched_list),
            quota_current=self.quota - len(self.matched_list),
            target_jobSeeker=target_seeker_name,
            current_message_from_jobSeeker=inbox_messages # ここにInboxの内容が入る
        )
        
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        # 相手(target_seeker)の発言はEnvironment側でメモリに追加済みとする
        # ここでは自分の返信をメモリに追加
        self.add_memory(target_seeker_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response
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
    # 修正: target_company_name 引数を削除 (LLMが決めるため)
    def act(self, active_companies_list, round_number, all_seeker_prefs, all_company_prefs, all_quotas):
        full_history = self.get_full_history()
        
        # 新しいプロンプトの変数に合わせて修正
        prompt = PROPOSER_PROMPT.format(
            name=self.name,
            preference=self.preferences,
            all_seeker_prefs=all_seeker_prefs,
            all_company_prefs=all_company_prefs,
            quota_text=all_quotas,
            full_history=full_history,
            round_number=round_number,
            active_company=str(active_companies_list)
        )
        
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        # ターゲット決定はLLMが行うため、environment側で処理できるようresponseに含まれる 'target' が重要になる
        # ここでは自身のメモリ追加は行わず、environment側でターゲットが有効か確認した後にメモリ追加する形をとる
        # (あるいはここで追加してもよいが、無効なターゲットだった場合の整合性が取りにくい)
        
        return response

class AccepterAgent(BaseAgent):
    """Company（企業）"""
    def __init__(self, name, preferences, quota=1):
        super().__init__(name, preferences)
        self.quota = quota
        self.matched_list = [] 

    # 修正: inbox_messages_str (全体) と target_seeker_name (個別) を受け取る
    def respond(self, target_seeker_name, inbox_messages_str, round_number, all_seeker_prefs, all_company_prefs):
        full_history = self.get_full_history()
        
        # 新しいプロンプトの変数に合わせて修正
        prompt = ACCEPTER_PROMPT.format(
            name=self.name,
            priority=self.preferences,
            all_seeker_prefs=all_seeker_prefs,
            all_company_prefs=all_company_prefs,
            quota=self.quota,
            full_history=full_history,
            round_number=round_number,
            matched_jobSeeker_list=str(self.matched_list),
            quota_current=self.quota - len(self.matched_list),
            current_message_from_jobSeeker=inbox_messages_str,
            target_jobSeeker=target_seeker_name
        )
        
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.7)
        
        # 自分(Company)の発言をメモリに記録
        self.add_memory(target_seeker_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response
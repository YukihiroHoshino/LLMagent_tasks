# src/agents.py
from .llm_client import get_llm_response
from .prompts import PROPOSER_PROMPT, ACCEPTER_PROMPT

class BaseAgent:
    def __init__(self, name, preferences):
        self.name = name
        self.preferences = preferences
        self.matched_partner = None
        # memory format: { "partner_name": [ {"role": "me/partner", "content": "...", "action": "..."} ] }
        self.memory = {}

    def get_full_history(self):
        """
        全相手との会話履歴をフォーマットして返す。
        """
        if not self.memory:
            return "No prior interactions with any agent."
        
        full_history_str = ""
        # 相手ごとにセクションを分ける
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
    def __init__(self, name, preferences, quotas):
        """
        Args:
            name (str): エージェント名
            preferences (list): 選好リスト
            quotas (dict): 全企業の定員情報 { "Company_A": 1, ... }
        """
        super().__init__(name, preferences)
        self.quotas = quotas  # 全企業の定員情報を保持
        
    def act(self, target_company_name, active_companies_list, round_number):
        full_history = self.get_full_history()

        # 定員情報をプロンプト用に整形 (例: "- Company_A: 1 seats")
        quota_lines = [f"- {c}: {q} seats" for c, q in self.quotas.items()]
        quota_text_str = "\n".join(quota_lines)
        
        # プロンプト内の変数名を新しい仕様に合わせる
        # active_company にはターゲット含む全ての未マッチ企業を渡す
        prompt = PROPOSER_PROMPT.format(
            preference=self.preferences,
            quota_text=quota_text_str,
            full_history=full_history,
            round_number=round_number,
            active_company=str(active_companies_list),
            target_company=target_company_name
        )
        
        # temperature=0.0を指定
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.0)
        
        # 自身の記憶に追加
        self.add_memory(target_company_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response

class AccepterAgent(BaseAgent):
    """Company（企業）"""
    def __init__(self, name, preferences, quota=1):
        super().__init__(name, preferences)
        self.quota = quota
        self.matched_list = [] # 名前リスト

    def respond(self, target_seeker_name, incoming_message, incoming_action, active_seekers_list, round_number):
        # 注意: 
        # プロンプト仕様で「History」と「Current Message」が別枠になっているため、
        # まだメモリにincoming_messageを追加せず、既存の履歴だけでHistoryを作る。
        
        full_history = self.get_full_history()
        
        # 受信メッセージの成形
        current_msg_formatted = f"[{incoming_action}] {incoming_message}"

        # プロンプト作成
        prompt = ACCEPTER_PROMPT.format(
            priority=self.preferences,
            quota=self.quota,
            full_history=full_history,
            round_number=round_number,
            active_jobSeeker=str(active_seekers_list),
            matched_jobSeeker_list=str(self.matched_list),
            quota_current=self.quota - len(self.matched_list),
            target_jobSeeker=target_seeker_name,
            current_message_from_jobSeeker=current_msg_formatted
        )
        
        # LLMコール (temperature=0.0)
        response = get_llm_response(system_prompt="", user_prompt=prompt, temperature=0.0)
        
        # ここで初めて「相手のメッセージ」と「自分の応答」をメモリに追加する
        # これにより、次回のラウンドではこれらがHistoryに含まれるようになる
        self.add_memory(target_seeker_name, "partner", incoming_message, incoming_action)
        self.add_memory(target_seeker_name, "me", response.get("message", ""), response.get("ACTION", ""))
        
        return response
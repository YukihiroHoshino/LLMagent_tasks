from src.agents.base_agent import BaseAgent
from src.llm.prompts import SEEKER_SYSTEM_TEMPLATE
from src.llm.parser import extract_action

class SeekerAgent(BaseAgent):
    def __init__(self, name, preference_list, traits="Pythonが得意"):
        super().__init__(name, traits)
        self.preference_list = preference_list 
        self.current_pref_index = 0
        self.status = "UNMATCHED" # UNMATCHED, MATCHED (Kept), REJECTED, DONE
        
    def get_current_target(self):
        if self.current_pref_index < len(self.preference_list):
            return self.preference_list[self.current_pref_index]
        return None

    def think_and_act(self, incoming_message=None):
        # --- 修正点: マッチ中（キープ中）なら何もしない ---
        if self.status == "MATCHED":
            return "（結果待ちのため待機中）", "WAIT"

        target = self.get_current_target()
        if not target:
            return "もう応募できる企業がありません...", "WITHDRAW"

        # システムプロンプトの構築
        system_prompt = SEEKER_SYSTEM_TEMPLATE.format(
            name=self.name,
            target_company=target,
            traits=self.traits
        )
        
        messages = [{"role": "system", "content": system_prompt}] + self.history
        
        # LLM実行
        response_text = self.llm.get_response(messages)
        action = extract_action(response_text)
        
        # 自分自身の発言を履歴に追加
        self.add_message("assistant", response_text)
        
        return response_text, action

    def receive_rejection(self):
        """拒否された場合、次の企業へ進む"""
        self.status = "UNMATCHED" # ステータスを戻す
        self.current_pref_index += 1
        self.reset_history()
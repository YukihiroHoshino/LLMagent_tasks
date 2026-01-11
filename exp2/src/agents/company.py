from src.agents.base_agent import BaseAgent
from src.llm.prompts import COMPANY_SYSTEM_TEMPLATE
from src.llm.parser import extract_action

class CompanyAgent(BaseAgent):
    def __init__(self, name, preference_list, quota=1, traits="成長企業"):
        super().__init__(name, traits)
        self.preference_list = preference_list # 求職者名のリスト（優先度順）
        self.quota = quota
        self.current_holders = [] # 現在キープしている求職者のリスト
        
    def get_applicant_rank(self, applicant_name):
        """応募者の順位を返す（数値が小さいほど優秀）"""
        try:
            return self.preference_list.index(applicant_name)
        except ValueError:
            return 999 # リストにない場合
            
    def think_and_act(self, applicant_name, applicant_message):
        # 応募者からのメッセージを履歴に追加
        self.add_message("user", f"{applicant_name}: {applicant_message}")
        
        # 現在の状況サマリー作成
        status_summary = f"現在のキープ者: {self.current_holders}, 定員: {self.quota}"
        
        system_prompt = COMPANY_SYSTEM_TEMPLATE.format(
            name=self.name,
            quota=self.quota,
            status_summary=status_summary,
            traits=self.traits
        )
        
        messages = [{"role": "system", "content": system_prompt}] + self.history
        
        response_text = self.llm.get_response(messages)
        action = extract_action(response_text)
        
        # 自分の発言を履歴に追加
        self.add_message("assistant", response_text)
        
        # ロジックによるActionの上書き（LLMの判断ミスを防ぐため、厳密なDAにするならここで制御）
        # 今回はLLMの判断を尊重しつつ、定員オーバー時の強制排除ロジックはMarket側またはここで補助する
        
        return response_text, action
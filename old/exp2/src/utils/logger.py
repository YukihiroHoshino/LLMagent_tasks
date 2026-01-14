import os
import json
from datetime import datetime

class SimulationLogger:
    def __init__(self, base_dir="logs"):
        # 実行日時ごとのフォルダを作成 (例: logs/run_20251216_143000)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = os.path.join(base_dir, f"run_{timestamp}")
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.conversation_log = []
        self.log_file_path = os.path.join(self.log_dir, "conversation_log.json")
        self.result_file_path = os.path.join(self.log_dir, "matching_result.json")

    def log_interaction(self, round_num, sender, receiver, message, action, step_type):
        """
        1回のやり取りを記録する
        step_type: 'seeker_action' or 'company_response'
        """
        entry = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "step_type": step_type,
            "sender": sender,
            "receiver": receiver,
            "action_tag": action,
            "message": message
        }
        self.conversation_log.append(entry)
        
        # リアルタイム性を重視して都度保存（または数回に一回でも可）
        self.save_conversations()

    def save_conversations(self):
        with open(self.log_file_path, "w", encoding="utf-8") as f:
            json.dump(self.conversation_log, f, indent=2, ensure_ascii=False)

    def save_results(self, companies):
        """最終結果を保存"""
        results = {}
        for company in companies:
            results[company.name] = {
                "final_holders": company.current_holders,
                "quota": company.quota
            }
        
        with open(self.result_file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
    def get_log_dir(self):
        return self.log_dir
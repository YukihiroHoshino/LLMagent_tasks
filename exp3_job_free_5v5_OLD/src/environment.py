# src/environment.py
import json
import random
import datetime
import os
from .agents import ProposerAgent, AccepterAgent

class MatchingSimulation:
    def __init__(self, preference_file="data/preferences.json"):
        self.preference_file = preference_file
        self.seekers = []
        self.companies = []
        self.quotas = {} # 事前に定義
        self.logs = {
            "experiment_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "rounds": [],
            "final_matches": {}
        }
        self.load_agents()

    def load_agents(self):
        # 1. まず選好データを読み込む
        with open(self.preference_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        job_seekers_data = data.get("job_seekers", {})
        companies_data = data.get("companies", {})

        # 2. エージェント生成の「前に」Quotaデータを読み込む
        base_path = "data"
        quota_path = os.path.join(base_path, "quota.json")
        
        if os.path.exists(quota_path):
            with open(quota_path, "r", encoding="utf-8") as f:
                self.quotas = json.load(f)
        else:
            # デフォルト値 (companies_dataのキーを使用)
            print("Warning: quota.json not found. Defaulting quotas to 1.")
            self.quotas = {c: 1 for c in companies_data.keys()}

        # 3. エージェントの生成 (読み込んだ quota を引数として渡す)
        
        # Job Seekers: 全企業の定員情報(self.quotas)を渡す
        for name, prefs in job_seekers_data.items():
            self.seekers.append(ProposerAgent(name, prefs, self.quotas))
            
        # Companies: 自社の定員数(quota)を渡す
        for name, prefs in companies_data.items():
            company_quota = self.quotas.get(name, 1)
            self.companies.append(AccepterAgent(name, prefs, quota=company_quota))

    def run(self):
        max_rounds = 100
        
        for round_count in range(1, max_rounds + 1):
            
            # 1. 未マッチングのエージェントオブジェクトを抽出
            active_seekers_objs = [s for s in self.seekers if s.matched_partner is None]
            active_companies_objs = [c for c in self.companies if len(c.matched_list) < c.quota]
            
            # 名前リストの作成（ターゲットも含めた全アクティブリスト）
            active_seekers_names = [s.name for s in active_seekers_objs]
            active_companies_names = [c.name for c in active_companies_objs]

            print(f"\n--- Round {round_count} ---")
            print(f"Active Seekers: {len(active_seekers_objs)}, Active Companies: {len(active_companies_objs)}")

            # 終了条件
            if len(active_seekers_objs) == 0 or len(active_companies_objs) == 0:
                print("All agents matched or quota filled.")
                break
            
            # 2. ランダムペアリング
            current_seekers = active_seekers_objs[:]
            current_companies = active_companies_objs[:]
            random.shuffle(current_seekers)
            random.shuffle(current_companies)
            
            num_pairs = min(len(current_seekers), len(current_companies))
            pairs = list(zip(current_seekers[:num_pairs], current_companies[:num_pairs]))
            
            round_logs = []
            
            # 3. 交渉実施
            for seeker, company in pairs:
                print(f"Negotiation: {seeker.name} <-> {company.name}")
                
                # Proposer Action
                # round_number と、ターゲットを含む全active企業リストを渡す
                seeker_res = seeker.act(company.name, active_companies_names, round_count)
                
                s_msg = seeker_res.get("message", "")
                s_action = seeker_res.get("ACTION", "[TALK]")
                s_thought = seeker_res.get("thought_process", "")
                
                conversation_log = [
                    {"sender": seeker.name, "action": s_action, "message": s_msg, "thought": s_thought}
                ]
                
                result_status = "CONTINUE"
                
                # Company Reaction
                c_action = "NONE"
                c_msg = ""
                
                if s_action == "[WITHDRAW]":
                    result_status = "WITHDRAWN"
                    # Withdrawの場合も相手のメモリには記録する（会話終了として）
                    company.add_memory(seeker.name, "partner", s_msg, s_action)
                else:
                    # round_number と、ターゲットを含む全active求職者リストを渡す
                    company_res = company.respond(seeker.name, s_msg, s_action, active_seekers_names, round_count)
                    
                    c_msg = company_res.get("message", "")
                    c_action = company_res.get("ACTION", "[TALK]")
                    c_thought = company_res.get("thought_process", "")
                    
                    conversation_log.append(
                        {"sender": company.name, "action": c_action, "message": c_msg, "thought": c_thought}
                    )
                    
                    # マッチング判定
                    if s_action == "[APPLY]" and c_action == "[ACCEPT]":
                        result_status = "MATCHED"
                        seeker.matched_partner = company.name
                        company.matched_list.append(seeker.name)
                        print(f"  >>> MATCH ESTABLISHED: {seeker.name} & {company.name}")
                    elif c_action == "[REJECT]":
                        result_status = "REJECTED"

                round_logs.append({
                    "pair": f"{seeker.name}-{company.name}",
                    "conversation": conversation_log,
                    "result": result_status
                })

            self.logs["rounds"].append({
                "round_id": round_count,
                "pairs": round_logs
            })
            
            if round_count == max_rounds:
                print("\nReached maximum round limit.")

        self.save_results()

    def save_results(self):
        # 最終結果の集計
        for s in self.seekers:
            self.logs["final_matches"][s.name] = s.matched_partner

        os.makedirs("data/logs", exist_ok=True)
        filename = f"data/logs/result_{self.logs['experiment_id']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)
        print(f"\nSimulation Finished. Results saved to {filename}")
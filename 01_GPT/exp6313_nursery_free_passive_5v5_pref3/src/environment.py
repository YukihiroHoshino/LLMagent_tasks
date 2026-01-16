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
        self.logs = {
            "experiment_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "rounds": [],
            "final_matches": {}
        }
        
        # 全選好情報を保持するための変数
        self.all_seeker_prefs_str = ""
        self.all_company_prefs_str = ""
        self.all_quotas_str = ""
        
        # main.pyからの参照用に定員情報を保持する辞書を追加
        self.quotas = {} 
        
        self.load_agents()

    def load_agents(self):
        with open(self.preference_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # エージェント生成
        for name, prefs in data.get("parents", {}).items():
            self.seekers.append(ProposerAgent(name, prefs))
            
        for name, prefs in data.get("nurseries", {}).items():
            # quotaは今回はデフォルト1だが、データにあればそこから読む想定
            quota = 1
            self.companies.append(AccepterAgent(name, prefs, quota))
            
            # --- 修正箇所: quotas辞書に情報を格納 ---
            self.quotas[name] = quota 

        # --- 完備情報用：全選好リストの文字列生成 ---
        
        # Job Seekers
        seeker_lines = []
        for name, prefs in data.get("parents", {}).items():
            seeker_lines.append(f"- {name}: {prefs}")
        self.all_seeker_prefs_str = "\n".join(seeker_lines)

        # Companies
        company_lines = []
        quota_lines = []
        for name, prefs in data.get("nurseries", {}).items():
            company_lines.append(f"- {name}: {prefs}")
            # quota情報の作成（Company側はデフォルト1と仮定、実際はオブジェクトから取得も可）
            quota_lines.append(f"- {name}: Capacity {self.quotas[name]}")
            
        self.all_company_prefs_str = "\n".join(company_lines)
        self.all_quotas_str = "\n".join(quota_lines)


    def run(self):
        max_rounds = 30
        
        for round_count in range(1, max_rounds + 1):
            
            active_seekers_objs = [s for s in self.seekers if s.matched_partner is None]
            active_companies_objs = [c for c in self.companies if len(c.matched_list) < c.quota]
            
            active_seekers_names = [s.name for s in active_seekers_objs]
            active_companies_names = [c.name for c in active_companies_objs]

            print(f"\n--- Round {round_count} ---")
            print(f"Active Seekers: {len(active_seekers_objs)}, Active Companies: {len(active_companies_objs)}")

            if len(active_seekers_objs) == 0 or len(active_companies_objs) == 0:
                print("All agents matched or quota filled.")
                break
            
            current_seekers = active_seekers_objs[:]
            current_companies = active_companies_objs[:]
            random.shuffle(current_seekers)
            random.shuffle(current_companies)
            
            num_pairs = min(len(current_seekers), len(current_companies))
            pairs = list(zip(current_seekers[:num_pairs], current_companies[:num_pairs]))
            
            round_logs = []
            
            for seeker, company in pairs:
                print(f"Negotiation: {seeker.name} <-> {company.name}")
                
                # --- Proposer Action ---
                # 完備情報を渡す (all_seeker_prefs, all_company_prefs, quotas)
                seeker_res = seeker.act(
                    target_company_name=company.name,
                    active_companies_list=active_companies_names,
                    round_number=round_count,
                    all_seeker_prefs=self.all_seeker_prefs_str,
                    all_company_prefs=self.all_company_prefs_str,
                    all_quotas=self.all_quotas_str
                )
                
                s_msg = seeker_res.get("message", "")
                s_action = seeker_res.get("ACTION", "[TALK]")
                s_thought = seeker_res.get("thought_process", "")
                
                conversation_log = [
                    {"sender": seeker.name, "action": s_action, "message": s_msg, "thought": s_thought}
                ]
                
                result_status = "CONTINUE"
                
                # --- Company Reaction ---
                c_action = "NONE"
                c_msg = ""
                
                if s_action == "[WITHDRAW]":
                    result_status = "WITHDRAWN"
                    company.add_memory(seeker.name, "partner", s_msg, s_action)
                else:
                    # 完備情報を渡す
                    company_res = company.respond(
                        target_seeker_name=seeker.name,
                        incoming_message=s_msg,
                        incoming_action=s_action,
                        active_seekers_list=active_seekers_names,
                        round_number=round_count,
                        all_seeker_prefs=self.all_seeker_prefs_str,
                        all_company_prefs=self.all_company_prefs_str
                    )
                    
                    c_msg = company_res.get("message", "")
                    c_action = company_res.get("ACTION", "[TALK]")
                    c_thought = company_res.get("thought_process", "")
                    
                    conversation_log.append(
                        {"sender": company.name, "action": c_action, "message": c_msg, "thought": c_thought}
                    )
                    
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
        for s in self.seekers:
            self.logs["final_matches"][s.name] = s.matched_partner

        os.makedirs("data/logs", exist_ok=True)
        filename = f"data/logs/result_{self.logs['experiment_id']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)
        print(f"\nSimulation Finished. Results saved to {filename}")
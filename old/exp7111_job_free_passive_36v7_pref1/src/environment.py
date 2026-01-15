import json
import random
import datetime
import os
from .agents import ProposerAgent, AccepterAgent

class MatchingSimulation:
    def __init__(self, preference_file="data/preferences.json", quota_file="data/quota.json"):
        self.preference_file = preference_file
        self.quota_file = quota_file  # 定員定義ファイルのパス
        self.seekers = []
        self.companies = []
        self.logs = {
            "experiment_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "rounds": [],
            "final_matches": {}
        }
        
        self.all_seeker_prefs_str = ""
        self.all_company_prefs_str = ""
        self.all_quotas_str = ""
        self.quotas = {} 
        
        self.load_agents()

    def load_agents(self):
        """設定ファイルからエージェントを読み込み、初期化する"""
        
        # 1. 選好データの読み込み
        if not os.path.exists(self.preference_file):
            raise FileNotFoundError(f"Preference file not found: {self.preference_file}")
        with open(self.preference_file, 'r', encoding='utf-8') as f:
            pref_data = json.load(f)

        # 2. 定員(Quota)データの読み込み
        quota_data = {}
        if os.path.exists(self.quota_file):
            with open(self.quota_file, 'r', encoding='utf-8') as f:
                quota_data = json.load(f)
        else:
            print(f"Warning: {self.quota_file} not found. Defaulting quotas to 1.")
        
        # Job Seekers (Proposers) の初期化
        for name, prefs in pref_data.get("job_seekers", {}).items():
            self.seekers.append(ProposerAgent(name, prefs))
            
        # Companies (Accepters) の初期化
        for name, prefs in pref_data.get("companies", {}).items():
            # data/quota.json から定員を取得。なければデフォルト1
            quota = quota_data.get(name, 1)
            
            self.companies.append(AccepterAgent(name, prefs, quota))
            self.quotas[name] = quota 

        # --- プロンプト用の共有情報テキストを生成 ---
        
        # 全求職者の選好リスト文字列
        seeker_lines = []
        for name, prefs in pref_data.get("job_seekers", {}).items():
            seeker_lines.append(f"- {name}: {prefs}")
        self.all_seeker_prefs_str = "\n".join(seeker_lines)

        # 全企業の選好リストと採用枠文字列
        company_lines = []
        quota_lines = []
        for c in self.companies:
            company_lines.append(f"- {c.name}: {c.preferences}")
            quota_lines.append(f"- {c.name}: Capacity {c.quota}")
            
        self.all_company_prefs_str = "\n".join(company_lines)
        self.all_quotas_str = "\n".join(quota_lines)


    def run(self):
        """シミュレーションのメインループ"""
        max_rounds = 30
        
        for round_count in range(1, max_rounds + 1):
            
            # --- 1. アクティブなエージェントの抽出 ---
            
            # Seeker: まだマッチしていない人のみ市場に残る
            active_seekers_objs = [s for s in self.seekers if s.matched_partner is None]
            
            # Company: マッチ人数が定員未満の企業のみ市場に残る
            active_companies_objs = [c for c in self.companies if len(c.matched_list) < c.quota]
            
            active_seekers_names = [s.name for s in active_seekers_objs]
            active_companies_names = [c.name for c in active_companies_objs]

            # デバッグ用: 現在の空き枠総数を計算
            total_open_slots = sum([(c.quota - len(c.matched_list)) for c in active_companies_objs])

            print(f"\n--- Round {round_count} ---")
            print(f"Active Seekers: {len(active_seekers_objs)}")
            print(f"Active Companies: {len(active_companies_objs)} (Total Open Slots: {total_open_slots})")

            # 終了条件: 求職者がいなくなる OR 受け入れ可能な企業がいなくなる
            if len(active_seekers_objs) == 0:
                print("Simulation Ended: All Job Seekers have been matched (or withdrawn).")
                break
            
            if len(active_companies_objs) == 0:
                print("Simulation Ended: All Company quotas are filled.")
                break
            
            # --- 2. ランダムペアリング (環境による強制割り当て) ---
            random.shuffle(active_seekers_objs)
            
            # 企業リストもシャッフル
            current_round_companies = list(active_companies_objs)
            random.shuffle(current_round_companies)

            # 企業ごとに担当する求職者リストを保持する辞書
            assignments = {c: [] for c in current_round_companies}

            # ラウンドロビン方式で割り当て
            for i, seeker in enumerate(active_seekers_objs):
                target_company = current_round_companies[i % len(current_round_companies)]
                assignments[target_company].append(seeker)

            round_logs = []

            # --- 3. 企業ごとのインタラクション実行 ---
            for company, assigned_seekers in assignments.items():
                if not assigned_seekers:
                    continue

                # 現在の残り枠表示
                current_slots = company.quota - len(company.matched_list)
                print(f"Negotiation Group: {company.name} (Slots: {current_slots}) vs {len(assigned_seekers)} Seekers")
                
                # --- Step A: 求職者からのメッセージ収集 (Inbox作成) ---
                seeker_responses = {} 
                inbox_messages = []

                for seeker in assigned_seekers:
                    # 求職者のアクション実行
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
                    
                    seeker_responses[seeker] = {
                        "message": s_msg,
                        "action": s_action,
                        "thought": s_thought
                    }
                    
                    inbox_messages.append(f"- From {seeker.name} [{s_action}]: {s_msg}")

                inbox_str = "\n".join(inbox_messages)

                # --- Step B: 企業からの返信 ---
                for seeker in assigned_seekers:
                    s_data = seeker_responses[seeker]
                    s_msg = s_data["message"]
                    s_action = s_data["action"]
                    
                    conversation_log = [
                        {"sender": seeker.name, "action": s_action, "message": s_msg, "thought": s_data["thought"]}
                    ]
                    
                    result_status = "CONTINUE"
                    c_action = "NONE"
                    c_msg = ""
                    c_thought = ""

                    if s_action == "[WITHDRAW]":
                        result_status = "WITHDRAWN"
                        company.add_memory(seeker.name, "partner", s_msg, s_action)
                    else:
                        company.add_memory(seeker.name, "partner", s_msg, s_action)

                        company_res = company.respond(
                            target_seeker_name=seeker.name,
                            inbox_messages=inbox_str, 
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
                        
                        # --- マッチング判定 ---
                        if s_action == "[APPLY]" and c_action == "[ACCEPT]":
                            # ここで改めて定員チェック (同ラウンド内で埋まったか確認)
                            if len(company.matched_list) < company.quota:
                                result_status = "MATCHED"
                                seeker.matched_partner = company.name
                                company.matched_list.append(seeker.name)
                                print(f"   >>> MATCH ESTABLISHED: {seeker.name} & {company.name} ({len(company.matched_list)}/{company.quota})")
                            else:
                                result_status = "FAILED (QUOTA FILLED)"
                                c_action = "[REJECT]" 
                                
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
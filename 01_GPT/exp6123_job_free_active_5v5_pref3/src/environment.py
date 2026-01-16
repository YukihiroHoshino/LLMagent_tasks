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
        self.quotas = {} # 企業ごとの定員管理
        self.logs = {
            "experiment_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "rounds": [],
            "final_matches": {}
        }
        
        self.all_seeker_prefs_str = ""
        self.all_company_prefs_str = ""
        self.all_quotas_str = ""
        
        self.load_agents()

    def load_agents(self):
        with open(self.preference_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Job Seekers
        for name, prefs in data.get("job_seekers", {}).items():
            self.seekers.append(ProposerAgent(name, prefs))
            
        # Companies
        for name, prefs in data.get("companies", {}).items():
            # quota情報の取得（デフォルト1）
            quota = data.get("quotas", {}).get(name, 1)
            # data構造にquotasがない場合のフォールバック（例としてcompaniesデータ内に記述がある場合など適宜調整）
            if "quotas" not in data:
                quota = 1

            self.companies.append(AccepterAgent(name, prefs, quota))
            self.quotas[name] = quota

        # --- テキスト情報生成（完備情報） ---
        self.all_seeker_prefs_str = "\n".join([f"- {s.name}: {s.preferences}" for s in self.seekers])
        
        company_lines = []
        quota_lines = []
        for c in self.companies:
            company_lines.append(f"- {c.name}: {c.preferences}")
            quota_lines.append(f"- {c.name}: Capacity {c.quota}")
            
        self.all_company_prefs_str = "\n".join(company_lines)
        self.all_quotas_str = "\n".join(quota_lines)

    def run(self):
        max_rounds = 30
        
        for round_count in range(1, max_rounds + 1):
            
            # --- 1. アクティブなエージェントの特定 ---
            # まだマッチしていない求職者
            active_seekers_objs = [s for s in self.seekers if s.matched_partner is None]
            
            # 定員に空きがある企業
            # ★重要: このリストはこのラウンド中固定されます。
            # Seeker Aが選んだからといって、ここから削除されることはありません。
            active_companies_objs = [c for c in self.companies if len(c.matched_list) < c.quota]
            active_companies_names = [c.name for c in active_companies_objs]

            print(f"\n--- Round {round_count} ---")
            print(f"Active Seekers: {len(active_seekers_objs)}, Active Companies: {len(active_companies_objs)}")

            if not active_seekers_objs or not active_companies_objs:
                print("All agents matched or quota filled.")
                break
            
            # --- PHASE 1: Proposer (Seeker) Selection ---
            # 全員がターゲットを選び終わるまで、結果は確定しません。
            # company_inboxes: { "CompanyA": [msg1, msg2], "CompanyB": [msg3] }
            company_inboxes = {c_name: [] for c_name in active_companies_names}
            
            # 公平性のためシャッフルするが、誰が先に選んでも選択肢(active_companies_names)は同じ
            random.shuffle(active_seekers_objs)
            
            print(">> Job Seekers are selecting targets...")
            for seeker in active_seekers_objs:
                
                # ここで渡す active_companies_names はループ内で変更されないため、
                # 全Seekerが同じ「空き枠のある企業リスト」を見ることができます。
                response = seeker.act(
                    active_companies_list=active_companies_names,
                    round_number=round_count,
                    all_seeker_prefs=self.all_seeker_prefs_str,
                    all_company_prefs=self.all_company_prefs_str,
                    all_quotas=self.all_quotas_str
                )
                
                target_name = response.get("target")
                message = response.get("message", "")
                action = response.get("ACTION", "[TALK]")
                
                # ターゲットが有効かチェック（リストに含まれているか）
                if target_name in active_companies_names:
                    # メモリ記録
                    seeker.add_memory(target_name, "me", message, action)
                    
                    # 企業のInboxへ配送（重複応募もここでリストに追加されるだけなのでOK）
                    company_inboxes[target_name].append({
                        "seeker_obj": seeker,
                        "message": message,
                        "action": action,
                        "thought": response.get("thought_process", "")
                    })
                    print(f"  - {seeker.name} -> {target_name} ({action})")
                else:
                    # 幻覚でリストにない企業を選んだ場合など
                    print(f"  ! {seeker.name} selected Invalid/Full Target: {target_name}")

            # --- PHASE 2: Accepter (Company) Response ---
            round_logs = []
            
            # 企業側の処理順序をシャッフル（マッチ成立の公平性のため）
            random.shuffle(active_companies_objs)
            
            print(">> Companies are responding...")
            for company in active_companies_objs:
                inbox = company_inboxes.get(company.name, [])
                if not inbox:
                    continue
                
                # Inbox内のメッセージ一覧テキストを作成
                inbox_text_lines = []
                for item in inbox:
                    inbox_text_lines.append(f"- From {item['seeker_obj'].name} [{item['action']}]: {item['message']}")
                inbox_text_full = "\n".join(inbox_text_lines)
                
                # 受信したメッセージを順次処理
                for item in inbox:
                    seeker = item['seeker_obj']
                    s_msg = item['message']
                    s_action = item['action']
                    
                    # すでに他の企業とマッチが決まってしまったSeekerかチェック
                    # (Seekerループ内では同時並行だが、Company処理はシーケンシャルなので、
                    #  Company AがAcceptした直後にCompany Bが処理する場合などを考慮)
                    if seeker.matched_partner is not None:
                         # 既に決まっているのでスキップ、あるいは「既に決まった」旨をログに残す
                         # ここでは便宜上スキップせず会話は成立させるが、マッチにはならない処理とする
                         pass

                    # 企業メモリへ追加
                    company.add_memory(seeker.name, "partner", s_msg, s_action)
                    
                    # 応答生成
                    # target_jobSeekerには現在の相手、current_messageにはInbox全体を渡す
                    response = company.respond(
                        target_seeker_name=seeker.name,
                        inbox_messages_str=inbox_text_full,
                        round_number=round_count,
                        all_seeker_prefs=self.all_seeker_prefs_str,
                        all_company_prefs=self.all_company_prefs_str
                    )
                    
                    c_msg = response.get("message", "")
                    c_action = response.get("ACTION", "[TALK]")
                    c_thought = response.get("thought_process", "")
                    
                    seeker.add_memory(company.name, "partner", c_msg, c_action)
                    
                    conversation_log = [
                        {"sender": seeker.name, "action": s_action, "message": s_msg, "thought": item['thought']},
                        {"sender": company.name, "action": c_action, "message": c_msg, "thought": c_thought}
                    ]
                    
                    result_status = "CONTINUE"
                    
                    # --- マッチング判定 ---
                    if s_action == "[APPLY]" and c_action == "[ACCEPT]":
                        # 1. Seekerが未定
                        # 2. Companyに空きがある (処理中に埋まる可能性があるためここで再確認)
                        if seeker.matched_partner is None and len(company.matched_list) < company.quota:
                            result_status = "MATCHED"
                            seeker.matched_partner = company.name
                            company.matched_list.append(seeker.name)
                            print(f"  ★ MATCH: {seeker.name} <==> {company.name}")
                        else:
                            # タッチの差で埋まった、またはSeekerが他で決まった
                            result_status = "FAILED" 
                            if len(company.matched_list) >= company.quota:
                                result_status = "FAILED_QUOTA_FILLED"
                            elif seeker.matched_partner is not None:
                                result_status = "FAILED_SEEKER_UNAVAILABLE"
                                
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

            # 全Seekerが決まったら終了
            if len([s for s in self.seekers if s.matched_partner is None]) == 0:
                print("All seekers matched.")
                break

        self.save_results()

    def save_results(self):
        for s in self.seekers:
            self.logs["final_matches"][s.name] = s.matched_partner

        os.makedirs("data/logs", exist_ok=True)
        filename = f"data/logs/result_{self.logs['experiment_id']}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, ensure_ascii=False)
        print(f"\nSimulation Finished. Results saved to {filename}")
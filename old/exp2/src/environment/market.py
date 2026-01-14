import time
from colorama import Fore, Style
from src.utils.logger import SimulationLogger

class MarketEnvironment:
    def __init__(self, seekers, companies):
        self.seekers = {s.name: s for s in seekers}
        self.companies = {c.name: c for c in companies}
        self.round = 0
        self.logger = SimulationLogger()
        print(f"📁 Logs will be saved to: {self.logger.get_log_dir()}")
        
    def run_round(self):
        self.round += 1
        print(f"\n{Fore.YELLOW}=== Round {self.round} ==={Style.RESET_ALL}")
        
        # MATCHEDの人も、他社に取られる可能性があるためリストには含めるが、
        # Seeker自身が「WAIT」を返すことで手番をスキップする
        active_seekers = [s for s in self.seekers.values() if s.status != "DONE"]
        
        # 全員がDONEまたは完全に確定(今回の簡易版ではWaitし続ける)なら終了
        # ただし、厳密なDAではRejectの連鎖があるため、Unmatchedな人がいなくなるまで回す
        really_active = [s for s in active_seekers if s.status == "UNMATCHED"]
        if not really_active and self.round > 1:
             # 全員MATCHEDまたはDONEなら収束とみなす判定を追加してもよい
             # ここでは簡易的にログ出力のみ
             print(f"Info: All seekers are currently MATCHED or DONE.")

        if not active_seekers:
            print("全ての求職者が終了状態です。")
            return False 
            
        is_any_action_taken = False

        for seeker in active_seekers:
            target_name = seeker.get_current_target()
            if not target_name:
                seeker.status = "DONE"
                continue
                
            company = self.companies[target_name]
            
            # --- Seeker Turn ---
            msg_s, action_s = seeker.think_and_act()

            # WAITなら何もしない（ログも出さない、あるいはデバッグログのみ）
            if action_s == "WAIT":
                continue

            is_any_action_taken = True
            print(f"\n{Fore.CYAN}[Seeker] {seeker.name} -> {company.name}{Style.RESET_ALL}")
            print(f"Action: {action_s}")
            print(f"Message: {msg_s}")
            
            self.logger.log_interaction(
                self.round, seeker.name, company.name, msg_s, action_s, "seeker_action"
            )
            
            # --- Company Turn (Reply) ---
            if action_s in ["APPLY", "TALK"]:
                print(f"{Fore.GREEN}[Company] {company.name} responding...{Style.RESET_ALL}")
                
                context_msg = f"[{action_s}] {msg_s}"
                msg_c, action_c = company.think_and_act(seeker.name, context_msg)
                
                print(f"Action: {action_c}")
                print(f"Message: {msg_c}")
                
                self.logger.log_interaction(
                    self.round, company.name, seeker.name, msg_c, action_c, "company_response"
                )
                seeker.add_message("user", f"{company.name}: {msg_c}")

                # --- マッチング判定 ---
                if action_s == "APPLY":
                    if action_c == "HOLD":
                        self._handle_hold(company, seeker)
                    elif action_c == "REJECT":
                        self._handle_reject(company, seeker)
                
                elif action_s == "TALK":
                    # TALKに対してHOLDが返ってきても、ロジック上は無視するがWarningは出さない
                    # LLMが「現状維持」のつもりでHOLDと出力するのは自然なため
                    pass
            
            time.sleep(1)

        # 誰も何もアクションしなかったら終了（全員Wait状態）
        if not is_any_action_taken:
            print("No actions taken in this round. Market stabilized.")
            return False

        return True

    def _handle_hold(self, company, seeker):
        if seeker.name in company.current_holders:
            return

        if len(company.current_holders) < company.quota:
            company.current_holders.append(seeker.name)
            seeker.status = "MATCHED" 
            print(f"✅ {company.name} kept {seeker.name}")
        else:
            # 入れ替えロジック
            current_worst_seeker_name = max(company.current_holders, key=lambda x: company.get_applicant_rank(x))
            worst_rank = company.get_applicant_rank(current_worst_seeker_name)
            new_rank = company.get_applicant_rank(seeker.name)
            
            if new_rank < worst_rank:
                print(f"🔄 {company.name} swapped {current_worst_seeker_name} for {seeker.name}")
                company.current_holders.remove(current_worst_seeker_name)
                
                # 追い出された人の処理
                displaced_seeker = self.seekers[current_worst_seeker_name]
                displaced_seeker.receive_rejection() # ここでUNMATCHEDになり、履歴リセット
                
                company.current_holders.append(seeker.name)
                seeker.status = "MATCHED"
            else:
                print(f"❌ {company.name} rejected {seeker.name} (Low rank)")
                self._handle_reject(company, seeker)

    def _handle_reject(self, company, seeker):
        seeker.receive_rejection()
        # status更新はreceive_rejection内で行われるが念のため確認
        # seeker.status = "UNMATCHED"
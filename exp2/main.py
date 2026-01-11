import json
import os
from src.agents.seeker import SeekerAgent
from src.agents.company import CompanyAgent
from src.environment.market import MarketEnvironment
from src.utils.generator import generate_preferences

def main():
    # 1. 設定
    seeker_names = ["Seeker_A", "Seeker_B", "Seeker_C"]
    company_names = ["Corp_X", "Corp_Y", "Corp_Z"]
    
    # 2. 選好リストの生成と保存
    prefs = generate_preferences(seeker_names, company_names)
    
    # データフォルダがなければ作成
    os.makedirs("data", exist_ok=True)
    with open("data/preferences.json", "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2, ensure_ascii=False)
    
    print("Preferences Generated:")
    print(json.dumps(prefs, indent=2, ensure_ascii=False))
    
    # 3. エージェントの初期化
    seekers = []
    for name in seeker_names:
        # Seekerごとの特徴
        traits = "Pythonが得意, 積極的" if name == "Seeker_A" else "Javaが得意, 慎重"
        seekers.append(SeekerAgent(name, prefs[name], traits))
        
    companies = []
    for name in company_names:
        companies.append(CompanyAgent(name, prefs[name], quota=1))
        
    # 4. マーケットの初期化と実行
    market = MarketEnvironment(seekers, companies)
    
    # ラウンド数を30に変更
    max_rounds = 30
    
    try:
        for _ in range(max_rounds):
            is_active = market.run_round()
            if not is_active:
                break
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    finally:
        # 5. 最終結果の表示と保存（エラーで止まっても保存する）
        print("\n=== Final Matching Results ===")
        for c in companies:
            print(f"{c.name}: {c.current_holders}")
            
        market.save_final_results()
        print(f"Results saved to {market.logger.get_log_dir()}")

if __name__ == "__main__":
    main()
import json
import itertools
import os

def load_data(pref_path, match_path):
    """JSONデータを読み込む"""
    if not os.path.exists(pref_path) or not os.path.exists(match_path):
        print("エラー: 指定されたファイルが見つかりません。")
        return None, None

    with open(pref_path, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    with open(match_path, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    
    return preferences, matches

def get_rank_dictionaries(preferences):
    """
    選好リストを辞書形式（{相手: 順位ランク}）に変換する。
    ランクは0始まりで、数字が小さいほど好ましい。
    例: ['A', 'B'] -> {'A': 0, 'B': 1}
    """
    seeker_ranks = {}
    for seeker, pref_list in preferences['job_seekers'].items():
        seeker_ranks[seeker] = {company: i for i, company in enumerate(pref_list)}
        
    company_ranks = {}
    for company, pref_list in preferences['companies'].items():
        company_ranks[company] = {seeker: i for i, seeker in enumerate(pref_list)}
        
    return seeker_ranks, company_ranks

def check_stability(matches, seeker_ranks, company_ranks):
    """
    安定性を判定し、ブロッキングペアがあればリストを返す。
    """
    blocking_pairs = []
    
    # マッチング結果の逆引き辞書を作成 (Company -> Seeker)
    match_s_to_c = matches['final_matches']
    match_c_to_s = {v: k for k, v in match_s_to_c.items()}
    
    seekers = list(seeker_ranks.keys())
    companies = list(company_ranks.keys())

    # 全ペア(s, c)についてブロッキングペアかどうか確認
    for s in seekers:
        current_partner_c = match_s_to_c.get(s)
        # 現在のパートナーの順位 (マッチしてなければ無限大)
        s_current_rank = seeker_ranks[s].get(current_partner_c, float('inf'))
        
        for c in companies:
            # 1. 求職者sにとって、cが現在の相手より好ましいか？
            s_rank_for_c = seeker_ranks[s].get(c, float('inf'))
            if s_rank_for_c < s_current_rank:
                
                # 2. 企業cにとっても、sが現在の相手より好ましいか？
                current_partner_s = match_c_to_s.get(c)
                c_current_rank = company_ranks[c].get(current_partner_s, float('inf'))
                c_rank_for_s = company_ranks[c].get(s, float('inf'))
                
                if c_rank_for_s < c_current_rank:
                    blocking_pairs.append((s, c))

    is_stable = (len(blocking_pairs) == 0)
    return is_stable, blocking_pairs

def get_utility_vector(match_dict, seeker_ranks, company_ranks):
    """
    マッチング全体の満足度（順位のリスト）を返す。
    値が小さいほど満足度が高い。
    """
    utilities = []
    # 求職者の満足度
    for s, c in match_dict.items():
        utilities.append(seeker_ranks[s][c])
    
    # 企業の満足度（match_dictから逆引きして計算）
    match_c_to_s = {v: k for k, v in match_dict.items()}
    for c in company_ranks.keys():
        s = match_c_to_s[c]
        utilities.append(company_ranks[c][s])
        
    return utilities

def check_pareto_efficiency(matches, seeker_ranks, company_ranks):
    """
    パレート効率性を判定する。
    他の全員を悪化させずに、誰かの満足度を向上させる別のマッチングが存在するか確認。
    """
    current_match = matches['final_matches']
    seekers = list(seeker_ranks.keys())
    companies = list(company_ranks.keys())
    
    # 現在のマッチングの効用（順位）ベクトル
    current_utilities = get_utility_vector(current_match, seeker_ranks, company_ranks)
    
    # 5! = 120通りの全組み合わせをチェック（人数が少ないため総当りが可能）
    # 企業側の並び順を順列で生成し、固定した求職者リストとマッチングさせる
    for p in itertools.permutations(companies):
        candidate_match = {seekers[i]: p[i] for i in range(len(seekers))}
        candidate_utilities = get_utility_vector(candidate_match, seeker_ranks, company_ranks)
        
        # 比較ロジック:
        # すべてのエージェントについて、候補案の順位 <= 現状の順位 (同等以上)
        better_or_equal = all(new <= old for new, old in zip(candidate_utilities, current_utilities))
        
        # 少なくとも一人のエージェントについて、候補案の順位 < 現状の順位 (厳密に改善)
        strictly_better = any(new < old for new, old in zip(candidate_utilities, current_utilities))
        
        if better_or_equal and strictly_better:
            # パレート改善となるマッチングが見つかった -> 現状はパレート効率的ではない
            return False, candidate_match

    return True, None

def main():
    pref_path = 'data/preferences.json'
    match_path = 'data/matching_result.json'
    
    print(f"Loading data from {pref_path} and {match_path}...")
    preferences, matches = load_data(pref_path, match_path)
    
    if preferences is None or matches is None:
        return

    # ランク辞書の作成
    seeker_ranks, company_ranks = get_rank_dictionaries(preferences)

    # 1. 安定性の判定
    is_stable, blocking_pairs = check_stability(matches, seeker_ranks, company_ranks)
    print("\n=== 判定結果: 安定性 ===")
    if is_stable:
        print("判定: 安定 (Stable) です。ブロッキングペアは存在しません。")
    else:
        print("判定: 不安定 (Unstable) です。")
        print("検出されたブロッキングペア (お互いに駆け落ちしたいペア):")
        for s, c in blocking_pairs:
            print(f"  - {s} と {c}")

    # 2. パレート効率性の判定
    is_pareto, better_match = check_pareto_efficiency(matches, seeker_ranks, company_ranks)
    print("\n=== 判定結果: パレート効率性 ===")
    if is_pareto:
        print("判定: パレート効率的 (Pareto Efficient) です。")
        print("これ以上、誰の不利益も生じさせずに改善することはできません。")
    else:
        print("判定: パレート効率的ではありません (Not Pareto Efficient)。")
        print("以下のマッチングに変更すれば、誰も損せず誰かが得をします:")
        print(f"  {better_match}")

if __name__ == "__main__":
    main()
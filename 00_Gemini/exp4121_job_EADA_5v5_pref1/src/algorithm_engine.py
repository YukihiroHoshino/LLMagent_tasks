import collections
import random
import copy

def run_da_algorithm(seekers_prefs, companies_prefs, quotas):
    """
    Capacitated Gale-Shapley (DA) Algorithm.
    
    Args:
        seekers_prefs (dict): {seeker: [company_list]}
        companies_prefs (dict): {company: [seeker_list]}
        quotas (dict): {company: capacity_int}
        
    Returns:
        dict: Final matching {Company: [Seeker1, Seeker2, ...]}
    """
    free_seekers = list(seekers_prefs.keys())
    matches = {c: [] for c in companies_prefs}
    proposals_count = {seeker: 0 for seeker in seekers_prefs}
    
    # Precompute rankings for O(1) check
    company_rankings = {}
    for company, prefs in companies_prefs.items():
        company_rankings[company] = {seeker: i for i, seeker in enumerate(prefs)}

    while free_seekers:
        seeker = free_seekers.pop(0)
        submitted_list = seekers_prefs.get(seeker, [])
        
        idx = proposals_count[seeker]
        if idx >= len(submitted_list):
            continue 
            
        company = submitted_list[idx]
        proposals_count[seeker] += 1
        
        if company not in company_rankings:
            free_seekers.insert(0, seeker)
            continue
            
        capacity = quotas.get(company, 1)
        current_matches = matches[company]
        rank_map = company_rankings[company]
        
        if len(current_matches) < capacity:
            current_matches.append(seeker)
        else:
            # Find worst matched candidate
            valid_matches = [m for m in current_matches if m in rank_map]
            
            if not valid_matches:
                current_matches.append(seeker)
            else:
                worst_match = max(valid_matches, key=lambda x: rank_map.get(x, float('inf')))
                worst_rank = rank_map.get(worst_match, float('inf'))
                new_rank = rank_map.get(seeker, float('inf'))
                
                if new_rank < worst_rank:
                    current_matches.remove(worst_match)
                    current_matches.append(seeker)
                    free_seekers.append(worst_match)
                else:
                    free_seekers.append(seeker)
                    
    return matches

import copy

def run_eada_enforced(seekers_prefs, companies_prefs, quotas):
    """
    EADA Enforced Algorithm (Corrected Version)
    
    テキストの定義に基づき以下の修正を行っています:
    1. Part 1 (DA) をラウンド制 (Simultaneous) で実行し、正確なステップ数を記録する。
    2. Part 2 (Waiver) において、'Last Step' (最も遅いステップ) のブロッキング求職者のみを対象にする。
    """
    # 求職者の希望リストのディープコピーを作成（変更を加えるため）
    current_seekers_prefs = copy.deepcopy(seekers_prefs)
    
    # 安全のためのループ上限
    max_loops = 100 
    loop_count = 0
    
    while loop_count < max_loops:
        loop_count += 1
        
        # 1. Part 1: ラウンド制DAを実行し、ログとマッチング結果を取得
        trace_log, da_matches = _run_simultaneous_da(current_seekers_prefs, companies_prefs, quotas)
        
        # 最終的な割り当てを作成（Discrepancyチェック用）
        final_assignments = {}
        for c, s_list in da_matches.items():
            for s in s_list:
                final_assignments[s] = c
        
        # 2. Part 2: Blocking Job Seekersの特定
        # 条件1 Prevention: そのステップで一時的に採用され、他人を拒否させた
        # 条件2 Discrepancy: 最終的なマッチング先がその企業ではない
        
        blocking_instances = [] # 形式: {'step': int, 'blocker': str, 'company': str}
        
        for event in trace_log:
            # log形式: {'step': int, 'blocker': str, 'company': str, 'type': 'rejection_caused'}
            blocker = event['blocker']
            company = event['company']
            step = event['step']
            
            # Discrepancyの確認: 最終的にその企業にいないか？
            final_match = final_assignments.get(blocker)
            
            if final_match != company:
                blocking_instances.append({
                    'step': step, 
                    'blocker': blocker, 
                    'company': company
                })
        
        # ブロッカーがいなければ終了（Part 1の結果がFinal）
        if not blocking_instances:
            return da_matches
        
        # 3. Last Step の特定
        # "The computer looks for the last step... in which a Job Seeker has become a blocking Job Seeker."
        max_step = max(b['step'] for b in blocking_instances)
        
        # Last Stepに該当するインスタンスのみを抽出
        target_instances = [b for b in blocking_instances if b['step'] == max_step]
        
        # 4. Waiverの適用 (リストからの削除)
        changed = False
        
        # 重複処理を防ぐためにセット化
        waivers_to_apply = set((b['blocker'], b['company']) for b in target_instances)
        
        for seeker, company in waivers_to_apply:
            if company in current_seekers_prefs[seeker]:
                current_seekers_prefs[seeker].remove(company)
                changed = True
        
        # 変更がなければ終了（無限ループ防止）
        if not changed:
            return da_matches
            
    return da_matches

def _run_simultaneous_da(seekers_prefs, companies_prefs, quotas):
    """
    ラウンド制 (Simultaneous) Deferred Acceptance アルゴリズム
    
    Returns:
        trace_log: [{'step': n, 'blocker': s, 'company': c, ...}, ...]
        matches: {company: [seekers]}
    """
    # 初期化
    # 誰がどの企業に仮内定しているか
    matches = {c: [] for c in companies_prefs}
    # 誰がまだ未定（Free）か
    free_seekers = list(seekers_prefs.keys())
    # 誰が何番目の希望まで応募したか
    proposals_count = {s: 0 for s in seekers_prefs}
    
    # 企業の選好順位を高速検索できるようにマップ化
    company_rankings = {c: {s: i for i, s in enumerate(prefs)} for c, prefs in companies_prefs.items()}
    
    trace_log = []
    step = 0
    
    while True:
        step += 1
        
        # このラウンドでのプロポーザル（応募）を集める辞書: {company: [applicants]}
        current_round_proposals = {c: [] for c in companies_prefs}
        
        # 未定の求職者が一斉に応募する
        active_seekers_in_round = []
        
        if not free_seekers:
            break
            
        # Freeな求職者が次の希望に応募
        candidates_to_process = list(free_seekers) # コピーを作成してループ
        free_seekers = [] # 一旦空にする（拒否されたら戻ってくる）
        
        has_new_proposals = False
        
        for seeker in candidates_to_process:
            pref_list = seekers_prefs.get(seeker, [])
            idx = proposals_count[seeker]
            
            if idx < len(pref_list):
                target_company = pref_list[idx]
                proposals_count[seeker] += 1
                
                if target_company in current_round_proposals:
                    current_round_proposals[target_company].append(seeker)
                    active_seekers_in_round.append(seeker)
                    has_new_proposals = True
                else:
                    # 存在しない企業への応募は即時却下扱いとし、次のラウンドで次に応募させる（またはここでFreeに戻す）
                    free_seekers.append(seeker)
            else:
                # 希望リスト尽きた
                pass

        if not has_new_proposals:
            break
            
        # 各企業が選考を行う
        for company, new_applicants in current_round_proposals.items():
            if not new_applicants and not matches[company]:
                continue
                
            # 現在の仮内定者 + 新規応募者
            current_holders = matches[company]
            all_candidates = current_holders + new_applicants
            
            # ランキングに基づいてソート（ランク外の人は除外される可能性あり）
            rank_map = company_rankings.get(company, {})
            
            # ランキングに含まれる人のみ有効
            valid_candidates = [s for s in all_candidates if s in rank_map]
            rejected_candidates_this_turn = [s for s in all_candidates if s not in rank_map]
            
            # 優先順位でソート (値が小さいほど高優先)
            valid_candidates.sort(key=lambda s: rank_map[s])
            
            capacity = quotas.get(company, 1)
            
            # 定員内で合格する人
            accepted = valid_candidates[:capacity]
            # 定員漏れで拒否される人
            rejected_capacity = valid_candidates[capacity:]
            
            # 新たに拒否されるリスト
            total_rejected = rejected_capacity + rejected_candidates_this_turn
            
            # マッチング更新
            matches[company] = accepted
            
            # 拒否された人をFreeに戻す
            for r in total_rejected:
                free_seekers.append(r)
            
            # ログ記録: "Blocker" の特定
            # 定義: "Temporarily admitted... caused other Job Seekers to be rejected"
            # つまり、今回合格リスト(accepted)に入っている人は、今回拒否された人(total_rejected)全員に対して「ブロック」を行っている
            
            if total_rejected and accepted:
                for blocker in accepted:
                    trace_log.append({
                        'type': 'rejection_caused',
                        'step': step,
                        'blocker': blocker,
                        'company': company
                    })
                    
    return trace_log, matches

def run_boston_algorithm(seekers_prefs, companies_prefs, quotas):
    """
    Boston Mechanism (Immediate Acceptance).
    """
    free_seekers = list(seekers_prefs.keys())
    matches = {c: [] for c in companies_prefs}
    proposals_idx = {seeker: 0 for seeker in seekers_prefs}
    full_companies = set()

    while free_seekers:
        # Collect proposals for this round
        current_round_proposals = collections.defaultdict(list) 
        next_round_seekers = []
        
        # 1. Proposal Phase
        for seeker in free_seekers:
            submitted_list = seekers_prefs.get(seeker, [])
            idx = proposals_idx[seeker]
            
            if idx >= len(submitted_list):
                continue 
            
            company = submitted_list[idx]
            proposals_idx[seeker] += 1
            
            if company in full_companies:
                # Immediate rejection if full, try next in next loop
                next_round_seekers.append(seeker)
            else:
                current_round_proposals[company].append(seeker)
        
        free_seekers = next_round_seekers
        
        # 2. Acceptance Phase (Permanent)
        for company, applicants in current_round_proposals.items():
            if not applicants: continue
            
            capacity = quotas.get(company, 1)
            filled = len(matches[company])
            seats_avail = capacity - filled
            
            c_pref = companies_prefs.get(company, [])
            valid_applicants = [a for a in applicants if a in c_pref]
            rejected_in_round = [a for a in applicants if a not in c_pref]
            
            # Sort by priority
            valid_applicants.sort(key=lambda s: c_pref.index(s))
            
            accepted = valid_applicants[:seats_avail]
            rejected = valid_applicants[seats_avail:]
            
            matches[company].extend(accepted)
            
            # Rejected return to free pool
            free_seekers.extend(rejected)
            free_seekers.extend(rejected_in_round)
            
            if len(matches[company]) >= capacity:
                full_companies.add(company)

        if not current_round_proposals and not free_seekers:
            break
            
    return matches

def run_rsd_algorithm(seekers_prefs, companies_prefs, quotas, seed=None):
    """
    Random Serial Dictatorship (RSD).
    """
    if seed is not None:
        random.seed(seed)
        
    seekers_order = list(seekers_prefs.keys())
    random.shuffle(seekers_order)
    
    matches = {c: [] for c in companies_prefs}
    remaining_capacity = {c: quotas.get(c, 1) for c in companies_prefs}
    
    for seeker in seekers_order:
        submitted_list = seekers_prefs.get(seeker, [])
        
        matched = False
        for company in submitted_list:
            if remaining_capacity.get(company, 0) > 0:
                # Check eligibility
                if seeker in companies_prefs.get(company, []):
                    matches[company].append(seeker)
                    remaining_capacity[company] -= 1
                    matched = True
                    break
    return matches

def run_ttc_algorithm(seekers_prefs, companies_prefs, quotas):
    """
    Top Trading Cycles (TTC) Algorithm.
    """
    matches = {c: [] for c in companies_prefs}
    active_seekers = list(seekers_prefs.keys())
    remaining_capacity = {c: quotas.get(c, 1) for c in companies_prefs}
    seeker_next_proposal_idx = {s: 0 for s in active_seekers}
    
    while active_seekers:
        graph = {}
        
        # 1. Seekers point to top available company
        for s in active_seekers:
            s_list = seekers_prefs.get(s, [])
            idx = seeker_next_proposal_idx[s]
            
            target = None
            while idx < len(s_list):
                c = s_list[idx]
                if remaining_capacity.get(c, 0) > 0:
                    target = c
                    seeker_next_proposal_idx[s] = idx 
                    break
                idx += 1
            if target:
                graph[s] = target
                
        # 2. Companies point to top available seeker
        active_companies = [c for c, cap in remaining_capacity.items() if cap > 0]
        if not active_companies and not graph:
            break
            
        for c in active_companies:
            c_pref = companies_prefs.get(c, [])
            target_s = next((s for s in c_pref if s in active_seekers), None)
            if target_s:
                graph[c] = target_s
                
        if not graph:
            break
            
        # 3. Find Cycles
        visited = set()
        cycles = []
        nodes = list(graph.keys())
        
        for node in nodes:
            if node in visited: continue
            path = []
            curr = node
            path_set = set()
            
            while curr in graph:
                if curr in path_set:
                    # Cycle detected
                    cycle = path[path.index(curr):]
                    cycles.append(cycle)
                    for n in cycle: visited.add(n)
                    for n in path: visited.add(n)
                    break
                if curr in visited:
                    break
                path_set.add(curr)
                path.append(curr)
                curr = graph[curr]
                
        if not cycles:
            break
            
        # 4. Execute Trades
        removed_seekers = set()
        for cycle in cycles:
            for entity in cycle:
                # If entity is Seeker, they get the company they pointed to
                if entity in active_seekers:
                    company = graph[entity]
                    matches[company].append(entity)
                    remaining_capacity[company] -= 1
                    removed_seekers.add(entity)
                    
        active_seekers = [s for s in active_seekers if s not in removed_seekers]
        
    return matches
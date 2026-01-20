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

def run_eada_algorithm(seekers_prefs, companies_prefs, quotas):
    """
    Efficiency-Adjusted Deferred Acceptance (EADA) Algorithm (Enforced Waiver).
    
    Iteratively runs DA, identifies 'blocking' students (who caused rejection but moved away),
    removes those blocking applications from their lists, and re-runs DA.
    """
    # Create a deep copy of seekers' preferences because we will modify them
    current_seekers_prefs = copy.deepcopy(seekers_prefs)
    
    while True:
        # 1. Run DA with Logging to track rejections
        trace_log, da_matches = _run_da_with_logging(current_seekers_prefs, companies_prefs, quotas)
        
        # 2. Identify Blocking Job Seekers
        blocking_instances = [] 
        
        # Map final assignments for easy lookup
        final_assignments = {} 
        for c, s_list in da_matches.items():
            for s in s_list:
                final_assignments[s] = c
                
        # Analyze trace log for "Prevention" & "Discrepancy"
        # event: {'blocker': seeker, 'company': company, ...}
        for event in trace_log:
            if event['type'] == 'rejection_caused':
                blocker = event['blocker']
                company = event['company']
                
                # Check Discrepancy: Did the blocker end up at 'company'?
                final_match = final_assignments.get(blocker)
                
                if final_match != company:
                    # Found a blocking instance
                    blocking_instances.append((blocker, company))
        
        if not blocking_instances:
            return da_matches
        
        # 3. Apply Waivers (Step 1 of Part 2)
        # Remove the blocking company from the blocker's preference list
        unique_blocks = set(blocking_instances)
        
        for seeker, company in unique_blocks:
            if company in current_seekers_prefs[seeker]:
                current_seekers_prefs[seeker].remove(company)
        
        # Loop continues to re-run DA (Step 2 of Part 2)

def _run_da_with_logging(seekers_prefs, companies_prefs, quotas):
    """
    Helper DA that returns a log of rejections to identify blockers.
    """
    free_seekers = list(seekers_prefs.keys())
    matches = {c: [] for c in companies_prefs}
    proposals_count = {seeker: 0 for seeker in seekers_prefs}
    company_rankings = {c: {s: i for i, s in enumerate(prefs)} for c, prefs in companies_prefs.items()}
    
    # Log events: {'type': 'rejection_caused', 'blocker': seeker, 'company': company}
    trace_log = []

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
            valid_matches = [m for m in current_matches if m in rank_map]
            
            if not valid_matches:
                 current_matches.append(seeker)
            else:
                worst_match = max(valid_matches, key=lambda x: rank_map.get(x, float('inf')))
                worst_rank = rank_map.get(worst_match, float('inf'))
                new_rank = rank_map.get(seeker, float('inf'))
                
                if new_rank < worst_rank:
                    # 'seeker' enters and causes 'worst_match' to be rejected.
                    # 'seeker' is a blocker for this specific rejection.
                    trace_log.append({
                        'type': 'rejection_caused',
                        'blocker': seeker,
                        'company': company
                    })
                    # Everyone else currently holding a seat is also "blocking" the victim
                    for holder in current_matches:
                        if holder != worst_match:
                             trace_log.append({
                                'type': 'rejection_caused',
                                'blocker': holder,
                                'company': company
                            })

                    current_matches.remove(worst_match)
                    current_matches.append(seeker)
                    free_seekers.append(worst_match) 
                else:
                    # 'seeker' is rejected.
                    # Current holders are blockers.
                    for holder in current_matches:
                        trace_log.append({
                            'type': 'rejection_caused',
                            'blocker': holder,
                            'company': company
                        })
                    free_seekers.append(seeker)
                    
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
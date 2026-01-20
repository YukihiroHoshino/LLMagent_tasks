import collections

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
    
    # matches: {Company: [List of Seekers]}
    matches = {c: [] for c in companies_prefs}
    
    proposals_count = {seeker: 0 for seeker in seekers_prefs}
    
    # Precompute rankings for O(1) check: {Company: {Seeker: Rank}}
    company_rankings = {}
    for company, prefs in companies_prefs.items():
        company_rankings[company] = {seeker: i for i, seeker in enumerate(prefs)}

    while free_seekers:
        seeker = free_seekers.pop(0)
        submitted_list = seekers_prefs.get(seeker, [])
        
        idx = proposals_count[seeker]
        if idx >= len(submitted_list):
            continue # Exhausted list
            
        company = submitted_list[idx]
        proposals_count[seeker] += 1
        
        if company not in company_rankings:
            # Invalid company
            free_seekers.insert(0, seeker)
            continue
            
        # Get Company Capacity
        capacity = quotas.get(company, 1)
        current_matches = matches[company]
        
        # Logic:
        # 1. If not full, accept temporarily
        # 2. If full, compare with the worst current match
        
        rank_map = company_rankings[company]
        
        if len(current_matches) < capacity:
            current_matches.append(seeker)
        else:
            # Find worst matched candidate
            # Filter matches that are actually in preference list (safety)
            valid_matches = [m for m in current_matches if m in rank_map]
            
            if not valid_matches:
                # Weird edge case, just append
                current_matches.append(seeker)
            else:
                # Higher index = Worse preference
                worst_match = max(valid_matches, key=lambda x: rank_map.get(x, float('inf')))
                worst_rank = rank_map.get(worst_match, float('inf'))
                new_rank = rank_map.get(seeker, float('inf'))
                
                if new_rank < worst_rank:
                    # New seeker is better
                    current_matches.remove(worst_match)
                    current_matches.append(seeker)
                    free_seekers.append(worst_match) # Rejected
                else:
                    # New seeker is rejected
                    free_seekers.append(seeker)
                    
    return matches
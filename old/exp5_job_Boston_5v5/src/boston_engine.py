def run_boston_algorithm(seekers_prefs, companies_prefs):
    """
    Boston Mechanism (Immediate Acceptance).
    Acceptances are final immediately.
    """
    # Initialize state
    free_seekers = list(seekers_prefs.keys())
    matches = {} # {Company: Seeker}
    
    # Track which preference index each seeker is currently at
    proposals_idx = {seeker: 0 for seeker in seekers_prefs}
    
    # Companies that are already full
    full_companies = set()

    round_num = 0
    while free_seekers:
        round_num += 1
        # Round-based processing
        current_round_proposals = {} # {Company: [List of Seekers applied this round]}
        
        # 1. Proposal Phase
        # Only free seekers propose
        remaining_seekers = []
        for seeker in free_seekers:
            submitted_list = seekers_prefs.get(seeker, [])
            idx = proposals_idx[seeker]
            
            if idx >= len(submitted_list):
                continue # No more preferences
            
            company = submitted_list[idx]
            
            if company in full_companies:
                # If company is already full, this proposal is wasted (instant rejection)
                # In Boston, usually you apply, get rejected. 
                # effectively we just increment index for next round
                proposals_idx[seeker] += 1
                remaining_seekers.append(seeker)
            else:
                if company not in current_round_proposals:
                    current_round_proposals[company] = []
                current_round_proposals[company].append(seeker)
                # Increment index for next time (if rejected)
                proposals_idx[seeker] += 1
        
        free_seekers = remaining_seekers # Seekers who applied to full companies are still free
        
        # 2. Acceptance Phase
        for company, applicants in current_round_proposals.items():
            # Sort applicants based on company's true preference
            c_pref = companies_prefs.get(company, [])
            
            # Filter applicants who are actually in company's pref list
            valid_applicants = [a for a in applicants if a in c_pref]
            
            if not valid_applicants:
                # All applicants were unacceptable
                free_seekers.extend(applicants)
                continue
                
            # Find the best one
            # Lower index in c_pref = better
            best_applicant = min(valid_applicants, key=lambda x: c_pref.index(x))
            
            # Match is FINAL
            matches[company] = best_applicant
            full_companies.add(company)
            
            # Others are rejected
            rejected = [a for a in applicants if a != best_applicant]
            free_seekers.extend(rejected)

        # Break if no one is free or no progress can be made
        if not current_round_proposals and not free_seekers:
            break
            
    return matches
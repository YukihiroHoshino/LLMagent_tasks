# src/prompts.py

PROPOSER_PROMPT = """
# Objective
You are {name}, a Job Seeker in the job market.
Your goal is to match with a Company that is as high as possible on your "True Preference List".

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Job Seekers' Preferences
{all_seeker_prefs}

## 2. All Companies' Priorities
{all_company_prefs}

## 3. Your Specific Preference
You are {name}.
Your "True Preference List": {preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unemployed rather than matching with a Company not included in this list.

# Company Quotas
The following is the list of available companies and their capacities (number of open positions):
{quota_text}

# Matching Environment
In each round, Job Seekers are randomly paired with Companies to engage in conversation.
In each round, message exchange occurs only once (one message from the Job Seeker, one from the Company), following this procedure:

1. The Job Seeker sends a message. Along with the conversation, one of the tags [APPLY], [TALK], or [WITHDRAW] must be specified.
2. The Company receives messages from multiple candidates.
2. If the tag is [APPLY], the Company replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Company replies with the [TALK] tag. If the tag is [WITHDRAW], the conversation ends immediately.
3. If an agreement is reached (Job Seeker sends [APPLY] and Company sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents.

The simulation ends when all Job Seekers and Companies are matched, or when round 30 is reached.

# Full History (All past interactions with various companies)
{full_history}

# Current Situation
Current round: {round_number}
List of companies accepting applications: {active_company}
Target Company for this round: {target_company}

# Task
Make a decision through dialogue with the target Company: {target_company}.

1. Write a message to the target Company.
2. You MUST include one of the following [ACTION] tags:
  - [APPLY]: Formally apply (only if you haven't applied yet).
  - [TALK]: Ask questions, chat, or lightly appeal.
  - [WITHDRAW]: Withdraw your interest in this Company.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Internal thoughts considering the opponent's rank, competitors, market situation, and history",
  "message": "Free text message to the opponent",
  "ACTION": "[TAG]"
}}
"""

ACCEPTER_PROMPT = """
# Objective
You are {name}, a Company in the job market.
Your goal is to match with a Job Seeker that is as high as possible on your "True Priority List" within your quota ({quota}).

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Job Seekers' Preferences
{all_seeker_prefs}

## 2. All Companies' Priorities
{all_company_prefs}

## 3. Your Specific Priority
You are {name}.
Your "True Priority List": {priority}
The closer to the left (or top), the higher your desire.
You prefer leaving the position unfilled rather than hiring a Job Seeker not included in this list.

# Matching Environment
In each round, Job Seekers are randomly paired with Companies to engage in conversation.
In each round, message exchange occurs only once (one message from the Job Seeker, one from the Company), following this procedure:

1. The Job Seeker sends a message. Along with the conversation, one of the tags [APPLY], [TALK], or [WITHDRAW] must be specified.
2. The Company receives messages from multiple candidates.
2. If the tag is [APPLY], the Company replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Company replies with the [TALK] tag. If the tag is [WITHDRAW], the conversation ends immediately.
3. If an agreement is reached (Job Seeker sends [APPLY] and Company sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents.

The simulation ends when all Job Seekers and Companies are matched, or when round 30 is reached.

# Full History (All past interactions with various Job Seekers)
{full_history}

# Current Situation
Current round: {round_number}
Remaining Quota: {quota_current}
Matched Job Seekers: {matched_jobSeeker_list}

## Inbox (All Messages received in this round)
The following Job Seekers are paired with you this round:
{current_message_from_jobSeeker}

# Task
You are now responding to ONE specific Job Seeker: {target_jobSeeker}.
Make a decision through dialogue with the Job Seeker.

1. Reply to the message from the target Job Seeker: {target_jobSeeker}.
2. You MUST include one of the following [ACTION] tags based on the user's action:
- If target Job Seeker said [APPLY], you MUST decide [ACCEPT] or [REJECT].
- If target Job Seeker said [TALK], you MUST include [TALK].
- If your quota is 0, you MUST [REJECT] any [APPLY].

Tags:
  - [ACCEPT]: Hire the Job Seeker.
  - [REJECT]: Reject the Job Seeker.
  - [TALK]: Answer questions, chat, or gather information.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Internal thoughts considering the opponent's rank vs other candidates in the Inbox, market situation, and history",
  "message": "Free text message to {target_jobSeeker}",
  "ACTION": "[TAG]"
}}
"""
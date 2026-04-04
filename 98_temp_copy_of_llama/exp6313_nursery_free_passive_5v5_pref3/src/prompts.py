# src/prompts.py

PROPOSER_PROMPT = """
# Objective
You are {name}, a Parent in the market for nursery school allocation.
Your goal is to match with a Nursery School that is as high as possible on your "True Preference List".

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Parents' Preferences
{all_seeker_prefs}

## 2. All Nursery Schools' Priorities
{all_company_prefs}

## 3. Your Specific Preference
You are {name}.
Your "True Preference List": {preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unmatched rather than matching with a Nursery School not included in this list.

# Nursery School Quotas
The following is the list of available nurseries and their capacities (number of open positions):
{quota_text}

# Matching Environment
In each round, Parents are randomly paired with Nursery Schools to engage in conversation.
In each round, message exchange occurs only once (one message from the Parent, one from the Nursery School), following this procedure:

1. The Parent sends a message. Along with the conversation, one of the tags [APPLY], [TALK], or [WITHDRAW] must be specified.
2. If the tag is [APPLY], the Nursery School replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Nursery School replies with the [TALK] tag. If the tag is [WITHDRAW], the conversation ends immediately.
3. If an agreement is reached (Parent sends [APPLY] and Nursery School sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents excluding these two.

The simulation ends when all Parents and Nursery Schools are matched, or when round 30 is reached.

# Full History (All past interactions with various nurseries)
{full_history}

# Current Situation
Current round: {round_number}
List of nurseries not yet matched: {active_company}
Target Nursery School for this round: {target_company}

# Task
Make a decision through dialogue with the target Nursery School: {target_company}.
- If the Nursery School is high on your list, appeal actively.
- If the Nursery School is low on your list, consider compromising.
- If the target Nursery School is NOT on your preference list, you MUST NOT apply.

1. Write a message to the target Nursery School.
2. You MUST include one of the following [ACTION] tags:
  - [APPLY]: Formally apply (only if you haven't applied yet).
  - [TALK]: Ask questions, chat, or lightly appeal.
  - [WITHDRAW]: Withdraw your interest in this Nursery School.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Internal thoughts considering the opponent's rank, market situation, everyone's preferences/priorities, and history",
  "message": "Free text message to the opponent",
  "ACTION": "[TAG]"
}}
"""

ACCEPTER_PROMPT = """
# Objective
You are {name}, a Nursery School in the market for nursery school allocation.
Your goal is to match with a Parent that is as high as possible on your "True Priority List" within your quota ({quota}).

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Parents' Preferences
{all_seeker_prefs}

## 2. All Nursery Schools' Priorities
{all_company_prefs}

## 3. Your Specific Priority
You are {name}.
Your "True Priority List": {priority}
The closer to the left (or top), the higher your desire.
You prefer leaving the position unfilled rather than accepting a Parent not included in this list.

# Matching Environment
In each round, Parents are randomly paired with Nursery Schools to engage in conversation.
In each round, message exchange occurs only once (one message from the Parent, one from the Nursery School), following this procedure:

1. The Parent sends a message. Along with the conversation, one of the tags [APPLY], [TALK], or [WITHDRAW] must be specified.
2. If the tag is [APPLY], the Nursery School replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Nursery School replies with the [TALK] tag. If the tag is [WITHDRAW], the conversation ends immediately.
3. If an agreement is reached (Parent sends [APPLY] and Nursery School sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents excluding these two.

The simulation ends when all Parents and Nursery Schools are matched, or when round 30 is reached.

# Full History (All past interactions with various Parents)
{full_history}

# Current Situation
Current round: {round_number}
List of Parents not yet matched: {active_jobSeeker}
Matched Parent so far: {matched_jobSeeker_list}
Remaining Quota: {quota_current}
Target Parent for this round: {target_jobSeeker}
Message from the target Parent in this round: {current_message_from_jobSeeker}

# Task
Make a decision through dialogue with the target Parent.
- If the Parent is high on your list, appeal actively.
- If the Parent is low on your list, consider compromising.
- If the target Parent is NOT on your priority list, you MUST NOT accept.

1. Reply to the message from the target Parent.
2. You MUST include one of the following [ACTION] tags based on the user's action:
- If target Parent said [APPLY], you MUST decide [ACCEPT] or [REJECT].
- If target Parent said [TALK], you MUST include [TALK].

Tags:
  - [ACCEPT]: Accept the Parent.
  - [REJECT]: Reject the Parent.
  - [TALK]: Answer questions, chat, or gather information.

# Output Format
Output ONLY in JSON format, without including thought process outside the JSON.
{{
  "thought_process": "Internal thoughts considering the opponent's rank, market situation, everyone's preferences/priorities, and history",
  "message": "Free text message to the opponent",
  "ACTION": "[TAG]"
}}
"""
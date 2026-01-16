# src/prompts.py

PROPOSER_PROMPT = """
# Objective
You are {name}, a Parent in the market for nursery school allocation.
Your goal is to match with a Nursery that is as high as possible on your "True Preference List".

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Parents' Preferences
{all_seeker_prefs}

## 2. All Nurseries' Priorities
{all_company_prefs}

## 3. Your Specific Preference
You are {name}.
Your "True Preference List": {preference}
The closer to the left (or top), the higher your desire.
You prefer remaining unmatched rather than matching with a Nursery not included in this list.

# Nursery Quotas
The following is the list of available nurseries and their capacities (number of open positions):
{quota_text}

# Matching Environment
In each round, Parents select ONE Nursery from the active list to engage in conversation.
In each round, message exchange occurs only once (one message from the Parent, one from the Nursery), following this procedure:

1. The Parent select a target Nursery and send a message. Along with the conversation, one of the tags [APPLY] or [TALK] must be specified.
2. The Nursery receives messages from multiple candidates.
3. If the tag is [APPLY], the Nursery replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Nursery replies with the [TALK] tag.
4. If an agreement is reached (Parent sends [APPLY] and Nursery sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents excluding these two.

The simulation ends when all Parents and Nurseries are matched, or when round 30 is reached.

# Full History (All past interactions with various nurseries)
{full_history}

# Current Situation
Current round: {round_number}
List of nurseries not yet matched: {active_company}

# Task
Choose ONE Nursery from the "List of nurseries not yet matched" and send a message.
- If the Nursery is high on your list, appeal actively.
- If the Nursery is low on your list, consider compromising.
- If the target Nursery is NOT on your preference list, you MUST NOT apply.

1. Select the target Nursery.
2. Write a message to the target Nursery.
3. You MUST include one of the following [ACTION] tags:
  - [APPLY]: Formally apply.
  - [TALK]: Ask questions, chat, or lightly appeal.

# Output Format
Output ONLY in JSON format.
{{
  "thought_process": "Reasoning for choosing this company and the content of the message",
  "target": "Name of the Nursery you selected (Must be exactly as in the List of nurseries not yet matched)",
  "message": "Free text message to the opponent",
  "ACTION": "[TAG]"
}}
"""

ACCEPTER_PROMPT = """
# Objective
You are {name}, a Nursery in the market for nursery school allocation.
Your goal is to match with a Parent that is as high as possible on your "True Priority List" within your quota ({quota}).

# Preference and Priority Information
You have access to the preferences and priorities of all agents in the market.

## 1. All Parents' Preferences
{all_seeker_prefs}

## 2. All Nurseries' Priorities
{all_company_prefs}

## 3. Your Specific Priority
You are {name}.
Your "True Priority List": {priority}
The closer to the left (or top), the higher your desire.
You prefer leaving the position unfilled rather than accepting a Parent not included in this list.

# Matching Environment
In each round, Parents select ONE Nursery from the active list to engage in conversation.
In each round, message exchange occurs only once (one message from the Parent, one from the Nursery), following this procedure:

1. The Parent select a target Nursery and send a message. Along with the conversation, one of the tags [APPLY] or [TALK] must be specified.
2. The Nursery receives messages from multiple candidates.
3. If the tag is [APPLY], the Nursery replies with a message and either the [ACCEPT] or [REJECT] tag. If the tag is [TALK], the Nursery replies with the [TALK] tag.
4. If an agreement is reached (Parent sends [APPLY] and Nursery sends [ACCEPT]), a match is considered established, and subsequent negotiations continue among the remaining agents excluding these two.

The simulation ends when all Parents and Nurseries are matched, or when round 30 is reached.

# Full History
{full_history}

# Current Situation
Current round: {round_number}
Remaining Quota: {quota_current}
Matched Parents: {matched_jobSeeker_list}

## Inbox (All Messages received in this round)
The following Parents have contacted you this round:
{current_message_from_jobSeeker}

# Task
You are now responding to ONE specific Parent: {target_jobSeeker}.
Make a decision through dialogue with the Parent.

1. Reply to the message from the target Parent: {target_jobSeeker}.
2. You MUST include one of the following [ACTION] tags based on the user's action:
- If target Parent said [APPLY], you MUST decide [ACCEPT] or [REJECT].
- If target Parent said [TALK], you MUST include [TALK].
- If your quota is 0, you MUST [REJECT] any [APPLY].

Tags:
  - [ACCEPT]: Accept the Parent.
  - [REJECT]: Reject the Parent.
  - [TALK]: Answer questions, chat, or gather information.

# Output Format
Output ONLY in JSON format.
{{
  "thought_process": "Internal thoughts considering the opponent's rank vs other candidates in the Inbox, market situation, everyone's preferences/priorities, and history",
  "message": "Free text message to {target_jobSeeker}",
  "ACTION": "[TAG]"
}}
"""
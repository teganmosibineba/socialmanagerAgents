"""
Social Media Manager - Multi-Agent System (Groq Edition)
=========================================================
Agents:
  1. OrchestratorAgent   - Routes tasks, coordinates all agents
  2. ContentAgent        - Generates platform-specific posts
  3. AnalystAgent        - Analyzes performance & gives insights
  4. SchedulerAgent      - Plans & manages posting schedules
  5. HashtagAgent        - Researches and suggests hashtags

Backend: Groq — llama-3.3-70b-versatile
Routing: OpenAI-compatible function calling
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from groq import Groq

# ── Load .env automatically ────────────────────────────────────────────────────
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

_load_env()

client = Groq()  # reads GROQ_API_KEY from env
MODEL  = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────
# Shared state (in-memory "database")
# ─────────────────────────────────────────────
state = {
    "posts":      [],
    "analytics":  [],
    "brand_voice": "friendly, professional, and engaging",
    "platforms":  ["Twitter/X", "Instagram", "LinkedIn", "Facebook"],
}

# ─────────────────────────────────────────────
# Helper: call any Groq model
# ─────────────────────────────────────────────

def _chat(system: str, user: str, max_tokens: int = 1024) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# Specialist Agents
# ─────────────────────────────────────────────

def content_agent(task: str, platform: str = "all", topic: str = "", tone: str = "") -> str:
    """Generates platform-optimised social media content."""
    system = f"""You are a specialist Social Media Content Writer.
Brand voice: {state['brand_voice']}
Available platforms: {', '.join(state['platforms'])}

Rules per platform:
- Twitter/X: max 280 chars, punchy, 1-2 hashtags inline
- Instagram: visual language, emojis welcome, 3-5 hashtags at end
- LinkedIn: professional tone, 150-300 words, thought-leadership angle
- Facebook: conversational, encourage engagement

Return ONLY a valid JSON object with platform names as keys and post content as values.
No markdown, no code fences, no explanation — just the JSON object."""

    prompt = f"""Create social media posts for: {topic or task}
Platform(s): {platform}
Tone: {tone or 'use brand voice'}"""

    result = _chat(system, prompt, max_tokens=1024)

    # Store drafts
    try:
        raw = re.search(r'\{.*\}', result, re.DOTALL)
        if raw:
            posts_data = json.loads(raw.group())
            for plat, content in posts_data.items():
                state["posts"].append({
                    "id":         len(state["posts"]) + 1,
                    "platform":   plat,
                    "content":    content,
                    "status":     "draft",
                    "created_at": datetime.now().isoformat(),
                    "topic":      topic or task,
                })
    except Exception:
        pass

    return result


def analyst_agent(task: str, platform: str = "all") -> str:
    """Analyzes social media performance and gives strategic insights."""
    if not state["analytics"]:
        state["analytics"] = [
            {"platform": "Twitter/X",  "followers": 12400, "engagement_rate": 3.2, "top_post_type": "threads",   "best_time": "9am-11am"},
            {"platform": "Instagram",  "followers": 28900, "engagement_rate": 5.7, "top_post_type": "carousels", "best_time": "6pm-8pm"},
            {"platform": "LinkedIn",   "followers": 8100,  "engagement_rate": 4.1, "top_post_type": "articles",  "best_time": "Tue-Thu 8am"},
            {"platform": "Facebook",   "followers": 15200, "engagement_rate": 2.8, "top_post_type": "videos",    "best_time": "1pm-3pm"},
        ]

    system = """You are a Social Media Analytics Expert.
Analyse the provided data and give:
1. Key performance insights with specific numbers
2. What's working and what's not
3. Concrete, actionable recommendations
4. Growth opportunities
Use bullet points for clarity."""

    prompt = f"""Analyse this social media data:
{json.dumps(state['analytics'], indent=2)}

Posts in pipeline: {len(state['posts'])}
Focus: {platform if platform != 'all' else 'all platforms'}
Question: {task}"""

    return _chat(system, prompt, max_tokens=1024)


def scheduler_agent(task: str, platform: str = "all", posts_per_week: int = 5) -> str:
    """Creates optimal posting schedules and manages the content calendar."""
    system = """You are a Social Media Scheduling Strategist.
Create data-driven posting schedules that maximise reach and engagement.
Consider: platform algorithms, audience time zones, content type, and frequency.
Return clear, actionable schedules with specific days and times."""

    drafts_summary = [
        {"id": p["id"], "platform": p["platform"], "topic": p["topic"], "status": p["status"]}
        for p in state["posts"]
    ]

    prompt = f"""Create a posting schedule.
Task: {task}
Platform(s): {platform}
Target posts/week: {posts_per_week}
Current drafts: {json.dumps(drafts_summary, indent=2)}
Today: {datetime.now().strftime('%A, %B %d %Y')}

Provide:
1. Weekly content calendar with specific days/times
2. Best posting windows per platform
3. Content mix ratio (educational/promotional/engaging)
4. Which drafts to post first and when"""

    result = _chat(system, prompt, max_tokens=1024)

    # Mark drafts as scheduled
    for post in state["posts"]:
        if post["status"] == "draft":
            post["status"] = "scheduled"

    return result


def hashtag_agent(task: str, platform: str = "Instagram", topic: str = "") -> str:
    """Researches trending hashtags and builds hashtag strategies."""
    system = """You are a Hashtag Research Specialist.
Hashtag strategy by platform:
- Instagram: mix of niche (10k-200k), medium (200k-1M), broad (1M+)
- Twitter/X: 1-2 highly relevant trending tags only
- LinkedIn: 3-5 professional industry tags
- Facebook: 1-3 very relevant tags maximum

Explain WHY each hashtag is recommended and its reach tier."""

    prompt = f"""Research hashtags for: {topic or task}
Platform: {platform}

Provide:
1. Primary hashtags (must-use, highest relevance)
2. Secondary hashtags (reach boosters)
3. Niche hashtags (targeted, lower competition)
4. Trending hashtags (if relevant)
5. Hashtags to AVOID and why"""

    return _chat(system, prompt, max_tokens=800)


# ─────────────────────────────────────────────
# Tool definitions (OpenAI function-calling format)
# ─────────────────────────────────────────────

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "content_agent",
            "description": "Generates platform-specific social media posts and captions. Use for: writing posts, creating content, drafting captions, repurposing content across platforms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task":     {"type": "string",  "description": "The content creation task"},
                    "platform": {"type": "string",  "description": "Target platform(s): Twitter/X, Instagram, LinkedIn, Facebook, or 'all'"},
                    "topic":    {"type": "string",  "description": "The topic or subject of the content"},
                    "tone":     {"type": "string",  "description": "Desired tone, e.g. humorous, inspirational, urgent"},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyst_agent",
            "description": "Analyses social media performance metrics and provides strategic insights. Use for: performance reports, engagement analysis, growth strategies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task":     {"type": "string", "description": "The analysis question or task"},
                    "platform": {"type": "string", "description": "Platform to focus on, or 'all'"},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scheduler_agent",
            "description": "Creates optimal posting schedules and content calendars. Use for: scheduling posts, planning content calendars, finding best posting times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task":           {"type": "string",  "description": "The scheduling task"},
                    "platform":       {"type": "string",  "description": "Platform(s) to schedule for"},
                    "posts_per_week": {"type": "integer", "description": "Desired posts per week"},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hashtag_agent",
            "description": "Researches and recommends hashtag strategies. Use for: finding hashtags, hashtag research, improving discoverability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task":     {"type": "string", "description": "The hashtag research task"},
                    "platform": {"type": "string", "description": "Target platform"},
                    "topic":    {"type": "string", "description": "Topic to find hashtags for"},
                },
                "required": ["task"],
            },
        },
    },
]

AGENT_MAP = {
    "content_agent":   content_agent,
    "analyst_agent":   analyst_agent,
    "scheduler_agent": scheduler_agent,
    "hashtag_agent":   hashtag_agent,
}


# ─────────────────────────────────────────────
# Orchestrator Agent
# ─────────────────────────────────────────────

def orchestrator(user_message: str, conversation_history: list) -> str:
    """
    Orchestrator — uses Groq function calling to delegate to specialist agents,
    collects their results, and synthesises a final response.
    """
    system = f"""You are the Social Media Manager Orchestrator — a senior strategist coordinating specialist AI agents.

Your team:
- content_agent   : writes posts & captions
- analyst_agent   : analyses performance & strategy
- scheduler_agent : plans posting calendars
- hashtag_agent   : researches hashtags

Current pipeline:
- Platforms: {', '.join(state['platforms'])}
- Brand voice: {state['brand_voice']}
- Posts: {len(state['posts'])} total ({len([p for p in state['posts'] if p['status']=='scheduled'])} scheduled, {len([p for p in state['posts'] if p['status']=='draft'])} drafts)

Instructions:
1. Understand the user's goal fully
2. Call the right agent(s) — you can call multiple in sequence
3. Chain results between agents when useful (e.g. content → hashtags)
4. Synthesise everything into one clear, helpful final response
5. Briefly explain what each agent did"""

    # Build message history for Groq (OpenAI format)
    messages = [{"role": "system", "content": system}]
    messages += conversation_history
    messages.append({"role": "user", "content": user_message})

    # Agentic loop
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            tools=AGENT_TOOLS,
            tool_choice="auto",
            messages=messages,
        )

        choice  = response.choices[0]
        message = choice.message

        # Append assistant turn to messages
        messages.append(message)

        # No tool calls → final answer
        if not message.tool_calls:
            return message.content or "Done."

        # Handle tool calls
        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            print(f"  🔧 Calling {fn_name}({', '.join(f'{k}={v!r}' for k, v in fn_args.items() if v)})...")

            agent_fn = AGENT_MAP.get(fn_name)
            result   = agent_fn(**fn_args) if agent_fn else f"Unknown agent: {fn_name}"

            # Feed tool result back
            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })
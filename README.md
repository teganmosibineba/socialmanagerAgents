# 🚀 Social Media Manager — Multi-Agent AI

A pure-Python multi-agent system powered by Claude that manages your entire social media presence.

## Architecture

```
User Input
    │
    ▼
┌──────────────────────────────┐
│      OrchestratorAgent       │  ← Claude with tool_use
│  Routes tasks, coordinates,  │
│  synthesises final response  │
└──────┬───────────────────────┘
       │  delegates via tool_use
       ├──────────────────────────────────┐
       │                                  │
       ▼                                  ▼
┌─────────────┐  ┌───────────────┐  ┌─────────────────┐  ┌────────────────┐
│ContentAgent │  │ AnalystAgent  │  │ SchedulerAgent  │  │  HashtagAgent  │
│             │  │               │  │                 │  │                │
│ Writes      │  │ Analyses      │  │ Plans content   │  │ Researches     │
│ platform-   │  │ performance   │  │ calendars &     │  │ trending tags  │
│ specific    │  │ & gives       │  │ optimal posting │  │ & hashtag      │
│ posts       │  │ insights      │  │ schedules       │  │ strategy       │
└─────────────┘  └───────────────┘  └─────────────────┘  └────────────────┘
       │
       ▼
   Shared State (in-memory)
   - posts[]      : drafts & scheduled content
   - analytics[]  : performance data
   - brand_voice  : consistent tone
   - platforms[]  : managed channels
```

## Setup

```bash
# 1. Install dependency
pip install anthropic

# 2. Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# 3. Run
python main.py
```

## Example Commands

| Goal | What to type |
|------|-------------|
| Create content | *"Write Instagram and LinkedIn posts about our new product launch"* |
| Get insights | *"Analyse our performance — what's working and what isn't?"* |
| Plan ahead | *"Create a 2-week content calendar for all platforms"* |
| Hashtags | *"Find the best hashtags for a fitness brand on Instagram"* |
| Schedule | *"Schedule this week's posts for maximum engagement"* |
| Multi-step | *"Write a Twitter thread about AI trends, research hashtags for it, then schedule it"* |

## Files

```
social_media_manager/
├── main.py           # CLI interface & conversation loop
├── agents.py         # All agents + orchestrator
├── requirements.txt
└── README.md
```

## Key Design Decisions

- **Pure Python** — only dependency is `anthropic`
- **Agentic loop** — orchestrator runs until `stop_reason == "end_turn"`, handles chained tool calls automatically
- **Multi-turn memory** — conversation history kept across turns (last 10 exchanges)
- **Shared state** — all agents read/write a central in-memory store
- **Tool-use routing** — orchestrator decides which agents to call and in what order

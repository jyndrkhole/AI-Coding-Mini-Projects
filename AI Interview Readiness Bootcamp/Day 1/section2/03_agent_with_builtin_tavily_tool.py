"""
===============================================================================
 Future with Shivank — AI Harness
 Section 2 · Script 03 · Use the vendor's ready-made LangChain tool (TavilySearch)
===============================================================================

WHAT THIS FILE TEACHES
----------------------
In Script 02 we wrapped the Tavily SDK in our own @tool. Tavily also publishes
an official LangChain integration, `langchain_tavily.TavilySearch`. Using it:

  • deletes our custom function — less code for us to maintain;
  • gives the LLM a much richer "menu card": besides `query`, the model may set
    optional arguments such as `include_domains`, `search_depth`, `time_range`
    or `topic`, all documented by the vendor;
  • keeps the tool up to date when the vendor's API changes.

    Script 02:  tools = [search]            ← our hand-written tool
    Script 03:  tools = [TavilySearch()]    ← vendor-maintained tool

Rule of thumb: if a well-maintained integration exists, prefer it over writing
your own wrapper.

PREREQUISITES (.env)
--------------------
    OPENAI_API_KEY=sk-...
    TAVILY_API_KEY=tvly-...

HOW TO RUN
----------
    uv run python 03_agent_with_builtin_tavily_tool.py
    uv run python 03_agent_with_builtin_tavily_tool.py "Which team won the most recent IPL final?"

EXPECTED OUTPUT (sample — live results change)
----------------------------------------------
    Hello from Future with Shivank — AI Harness!
    Tool name the LLM sees: tavily_search
    Question: Find 3 upcoming AI or developer meetups in Bengaluru and give the date, venue and a link for each.

    The agent produced 4 messages:
      [0] HumanMessage : Find 3 upcoming AI or developer meetups in Bengaluru ...
      [1] AIMessage    : 🛠  tool call → tavily_search({'query': 'upcoming AI developer meetups Bengaluru',
                                                         'time_range': 'month', 'topic': 'general'})
      [2] ToolMessage  : (tavily_search) {"query": "upcoming AI developer meetups Bengaluru", "follow_up_questions": null, "answer": null, "images": [], "results": [{"title": "... Bengaluru | Meetup", ...
      [3] AIMessage    : Here are 3 upcoming meetups in Bengaluru: ...

    FINAL ANSWER:
    Here are 3 upcoming meetups in Bengaluru:
    1) <meetup name> — <date> — <venue> — https://www.meetup.com/...
    2) ...

WHAT TO NOTICE
--------------
The tool is now called `tavily_search`, and the LLM chose EXTRA arguments
(time_range='month', topic='general') on its own, because the vendor's tool
description tells it those options exist. Our own tool in Script 02 only
offered `query`.
===============================================================================
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from langchain.agents import create_agent  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langchain_tavily import TavilySearch  # noqa: E402

from agent_trace_printer import print_agent_trace  # noqa: E402

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

DEFAULT_QUESTION = (
    "Find 3 upcoming AI or developer meetups in Bengaluru and give the date, "
    "venue and a link for each."
)

# Groq counts the prompt plus the reserved reply against an 8,000-token limit.
# With no max_tokens, this model reserves its full output budget and the
# request is rejected before Tavily runs.
llm = ChatOpenAI(
    model=GROQ_MODEL,
    api_key=os.environ["GROQ_API_KEY"],
    base_url=GROQ_BASE_URL,
    max_tokens=1024,
)

# A ready-made LangChain tool. Like TavilyClient, it reads TAVILY_API_KEY from
# the environment. Fewer, shorter results keep the agent prompt under Groq's
# token limit.
search_tool = TavilySearch(
    max_results=3,
    search_depth="basic",
    include_answer=False,
    include_raw_content=False,
)
tools = [search_tool]
agent = create_agent(model=llm, tools=tools)


def main() -> None:
    print("Hello from Future with Shivank — AI Harness!")
    print(f"Tool name the LLM sees: {search_tool.name}")

    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    print(f"Question: {question}")

    result = agent.invoke({"messages": [HumanMessage(content=question)]})
    print_agent_trace(result)


# ↑ Peek at the vendor's "menu card" yourself:
#   uv run python -c "from langchain_tavily import TavilySearch; import os; os.environ.setdefault('TAVILY_API_KEY','x'); t=TavilySearch(); print(t.name); print(t.args)"
#   → tavily_search
#   → {'query': {...}, 'include_domains': {...}, 'exclude_domains': {...}, 'search_depth': {...},
#      'include_images': {...}, 'time_range': {...}, 'topic': {...}, 'start_date': {...}, 'end_date': {...}}


if __name__ == "__main__":
    main()

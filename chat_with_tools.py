"""
chat_with_tools.py
==================
Example: streaming + tool-calls via the Experiential gateway (gpt-6-astra).

Streaming and tool-call behaviour is preserved exactly — only the base URL
and API key have changed (handled inside llm_client.build_client).
"""

import json
from llm_client import build_client, MODEL_ASTRA

# ── Tool definition ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city, e.g. 'London'",
                    }
                },
                "required": ["city"],
            },
        },
    }
]


def fake_weather_tool(city: str) -> str:
    """Simulated tool response (replace with a real API call if desired)."""
    return json.dumps({"city": city, "temperature": "22°C", "condition": "Partly cloudy"})


# ── Streaming + tool-call loop ───────────────────────────────────────────────

def run_tool_call_conversation():
    client = build_client(MODEL_ASTRA)
    messages = [{"role": "user", "content": "What's the weather like in Paris right now?"}]

    print("\n── Streaming first response ─────────────────────────────────────")
    stream = client.chat.completions.create(
        model=MODEL_ASTRA,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        stream=True,
    )

    # Accumulate streamed chunks
    collected_chunks = []
    collected_tool_calls: dict[int, dict] = {}

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue

        # Print streamed text content
        if delta.content:
            print(delta.content, end="", flush=True)

        # Accumulate tool-call deltas
        if delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                if idx not in collected_tool_calls:
                    collected_tool_calls[idx] = {
                        "id": tc.id or "",
                        "type": "function",
                        "function": {"name": tc.function.name or "", "arguments": ""},
                    }
                if tc.function.arguments:
                    collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments
                if tc.id:
                    collected_tool_calls[idx]["id"] = tc.id
                if tc.function.name:
                    collected_tool_calls[idx]["function"]["name"] = tc.function.name

        collected_chunks.append(chunk)

    print()  # newline after stream

    # If tool calls were requested, execute them and continue
    if collected_tool_calls:
        tool_calls_list = list(collected_tool_calls.values())
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls_list,
        })

        for tc in tool_calls_list:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            print(f"\n── Tool called: {fn_name}({fn_args}) ──")

            if fn_name == "get_current_weather":
                result = fake_weather_tool(**fn_args)
            else:
                result = json.dumps({"error": f"Unknown tool: {fn_name}"})

            print(f"   Tool result : {result}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

        print("\n── Streaming final response (with tool result) ──────────────────")
        final_stream = client.chat.completions.create(
            model=MODEL_ASTRA,
            messages=messages,
            stream=True,
        )
        for chunk in final_stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                print(delta.content, end="", flush=True)
        print()


if __name__ == "__main__":
    run_tool_call_conversation()

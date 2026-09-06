# Experiential Gateway — gpt-6-astra Integration

Routes all `gpt-6-astra` LLM calls through the
[Experiential Labs gateway](https://api.experientiallabs.ai/v1) instead of the OpenAI endpoint.

## Files

| File | Purpose |
|------|---------|
| `llm_client.py` | **Single source of truth.** Factory that returns an `openai.OpenAI` client pointed at the Experiential gateway for `gpt-6-astra`, or standard OpenAI for any other model. |
| `test_experiential.py` | Smoke-test: one call → prints reply + token usage. Run this first. |
| `chat_with_tools.py` | Full example preserving streaming and tool-calls. |
| `requirements.txt` | `openai>=1.30.0` |

## Quick start

```powershell
# 1. Install dependency
pip install -r requirements.txt

# 2. Set your Experiential API key (get it at Settings → API keys)
$env:EXPLABS_API_KEY = "exl-..."

# 3. Smoke-test (prints reply + token usage)
python test_experiential.py

# 4. Full streaming + tool-call demo
python chat_with_tools.py
```

## How the gateway swap works

`llm_client.build_client(model)` is the only place an `openai.OpenAI` instance
is ever created. For `gpt-6-astra` it passes:

```python
OpenAI(
    base_url="https://api.experientiallabs.ai/v1",
    api_key=os.environ["EXPLABS_API_KEY"],
)
```

Streaming (`stream=True`) and tool-calls (`tools=[...]`) are passed straight
through to the gateway — no other changes needed.

## Adding gpt-6-astra to your own code

Replace any direct `OpenAI(...)` construction for this model with:

```python
from llm_client import build_client, MODEL_ASTRA

client = build_client(MODEL_ASTRA)
response = client.chat.completions.create(
    model=MODEL_ASTRA,
    messages=[...],
    # stream=True, tools=[...] all work unchanged
)
```

"""
chat.py
=======
Terminal chat with gpt-6-astra via the Experiential gateway.
Works just like a ChatGPT / Claude conversation — type a message, get a reply.

Usage:
    python chat.py

Commands during chat:
    /new      - Start a fresh conversation (clears history)
    /usage    - Show token usage for this session
    /exit     - Quit
    Ctrl+C    - Quit
"""

import sys
import os

# ── Encoding fix for Windows terminals ──────────────────────────────────────
if hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from llm_client import build_client, MODEL_ASTRA

# ── Colours (work on most modern Windows terminals) ──────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
RED    = "\033[91m"

def colour(text: str, *codes: str) -> str:
    return "".join(codes) + text + RESET


# ── Session state ────────────────────────────────────────────────────────────

def new_session() -> tuple[list, dict]:
    """Return a fresh message history and usage counter."""
    system_msg = {
        "role": "system",
        "content": (
            "You are a helpful, knowledgeable assistant. "
            "Be concise but complete. "
            "When writing code, include brief explanations."
        ),
    }
    return [system_msg], {"prompt": 0, "completion": 0, "total": 0}


def print_banner(model: str, base_url: str) -> None:
    width = 62
    print()
    print(colour("=" * width, CYAN, BOLD))
    print(colour(f"  gpt-6-astra  |  Experiential Gateway Chat", CYAN, BOLD))
    print(colour(f"  Model   : {model}", DIM))
    print(colour(f"  Gateway : {base_url}", DIM))
    print(colour("-" * width, CYAN))
    print(colour("  Commands: /new  /usage  /exit  |  Ctrl+C to quit", DIM))
    print(colour("=" * width, CYAN, BOLD))
    print()


def print_usage(usage: dict) -> None:
    print(colour(
        f"\n  [Session tokens]  "
        f"Prompt: {usage['prompt']}  "
        f"Completion: {usage['completion']}  "
        f"Total: {usage['total']}",
        DIM,
    ))


# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    from llm_client import EXPERIENTIAL_BASE_URL
    client = build_client(MODEL_ASTRA)  # exits if key missing

    print_banner(MODEL_ASTRA, EXPERIENTIAL_BASE_URL)
    messages, session_usage = new_session()

    while True:
        # ── Prompt ──────────────────────────────────────────────────────────
        try:
            user_input = input(colour("You: ", GREEN, BOLD)).strip()
        except (KeyboardInterrupt, EOFError):
            print(colour("\n\nGoodbye!\n", YELLOW))
            break

        if not user_input:
            continue

        # ── Built-in commands ────────────────────────────────────────────────
        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            print(colour("\nGoodbye!\n", YELLOW))
            break

        if user_input.lower() == "/new":
            messages, session_usage = new_session()
            print(colour("\n  [New conversation started]\n", YELLOW))
            continue

        if user_input.lower() == "/usage":
            print_usage(session_usage)
            print()
            continue

        # ── API call with streaming ──────────────────────────────────────────
        messages.append({"role": "user", "content": user_input})

        print(colour("\nAssistant: ", CYAN, BOLD), end="", flush=True)

        try:
            stream = client.chat.completions.create(
                model=MODEL_ASTRA,
                messages=messages,
                stream=True,
            )
        except Exception as exc:
            print(colour(f"\n[ERROR] {exc}\n", RED))
            messages.pop()  # remove the user message that failed
            continue

        # Stream and collect reply
        reply_chunks = []
        usage_from_stream = None

        for chunk in stream:
            if not chunk.choices:
                # Some gateways send a final chunk with usage and no choices
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_from_stream = chunk.usage
                continue

            delta = chunk.choices[0].delta
            if delta and delta.content:
                print(delta.content, end="", flush=True)
                reply_chunks.append(delta.content)

            # Capture usage if included in the stream (not all gateways do)
            if hasattr(chunk, "usage") and chunk.usage:
                usage_from_stream = chunk.usage

        print("\n")  # blank line after reply

        # Store assistant reply in history
        full_reply = "".join(reply_chunks)
        messages.append({"role": "assistant", "content": full_reply})

        # Update session token counts
        if usage_from_stream:
            session_usage["prompt"]     += usage_from_stream.prompt_tokens or 0
            session_usage["completion"] += usage_from_stream.completion_tokens or 0
            session_usage["total"]      += usage_from_stream.total_tokens or 0

            print(colour(
                f"  [tokens: +{usage_from_stream.total_tokens or '?'}  "
                f"session total: {session_usage['total']}]",
                DIM,
            ))
            print()


if __name__ == "__main__":
    main()

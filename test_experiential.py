"""
test_experiential.py
====================
Smoke-test: makes ONE call to gpt-6-astra via the Experiential gateway and
prints the reply text + full token-usage breakdown, so you can confirm the
request is being billed to your Experiential credits.

Run with:
    python test_experiential.py
"""

import sys
# Force UTF-8 output so box-drawing chars work on every Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from llm_client import build_client, MODEL_ASTRA, EXPERIENTIAL_BASE_URL

SEP = "-" * 60

def main():
    print("=" * 60)
    print("  Experiential Gateway - smoke test")
    print(f"  Model   : {MODEL_ASTRA}")
    print(f"  Base URL: {EXPERIENTIAL_BASE_URL}")
    print("=" * 60)

    client = build_client(MODEL_ASTRA)  # exits if EXPLABS_API_KEY is missing

    try:
        response = client.chat.completions.create(
            model=MODEL_ASTRA,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise assistant. "
                        "Reply in at most two sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Confirm you are running through the Experiential gateway "
                        "and tell me today's date."
                    ),
                },
            ],
        )
    except Exception as exc:
        print(f"\n[ERROR] API call failed:\n  {exc}", file=sys.stderr)
        print(
            "\nCommon causes:\n"
            "  - Invalid or expired EXPLABS_API_KEY\n"
            "  - Network / firewall issue\n"
            "  - Model 'gpt-6-astra' not available on your plan\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # -- Reply ------------------------------------------------------------------
    reply = response.choices[0].message.content
    print(f"\n{SEP}")
    print("  Model reply")
    print(SEP)
    print(reply)

    # -- Token usage ------------------------------------------------------------
    usage = response.usage
    print(f"\n{SEP}")
    print("  Token usage")
    print(SEP)
    if usage:
        print(f"  Prompt tokens     : {usage.prompt_tokens}")
        print(f"  Completion tokens : {usage.completion_tokens}")
        print(f"  Total tokens      : {usage.total_tokens}")
    else:
        print("  (usage information not returned by the gateway)")

    # -- Finish reason ----------------------------------------------------------
    finish_reason = response.choices[0].finish_reason
    print(f"\n  Finish reason : {finish_reason}")
    print(f"\n{'=' * 60}")
    print("  TEST PASSED - request routed through Experiential gateway.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

import argparse

from .agent import DialogueAgent
from .nlu_backends import build_nlu_backend


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the vehicle dialogue Agent demo.")
    parser.add_argument("--query", help="single query mode")
    parser.add_argument("--sender-id", default="demo")
    parser.add_argument("--nlu-backend", choices=("rule", "remote"), help="override VOICE_AGENT_NLU_BACKEND")
    parser.add_argument("--nlu-url", help="remote NLU endpoint when using --nlu-backend remote")
    parser.add_argument("--nlu-timeout", type=float, help="remote NLU request timeout in seconds")
    args = parser.parse_args()

    agent = DialogueAgent(
        nlu_backend=build_nlu_backend(args.nlu_backend, args.nlu_url, args.nlu_timeout)
    )
    if args.query:
        _print_frames(agent.handle_as_dicts(args.query, args.sender_id))
        return

    print("VoiceAgent MCP Dialogue. Type 'exit' to quit.")
    while True:
        query = input("> ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        _print_frames(agent.handle_as_dicts(query, args.sender_id))


def _print_frames(frames: list[dict]) -> None:
    for frame in frames:
        if frame["status"] == "delta":
            print(frame["content"], end="", flush=True)
    print()
    print(
        {
            "intent": frames[-1]["intent"],
            "function": frames[-1]["function"],
            "slots": frames[-1]["slots"],
            "metadata": frames[-1]["metadata"],
        }
    )


if __name__ == "__main__":
    main()

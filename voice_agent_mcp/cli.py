import argparse

from .agent import DialogueAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the vehicle dialogue Agent demo.")
    parser.add_argument("--query", help="single query mode")
    parser.add_argument("--sender-id", default="demo")
    args = parser.parse_args()

    agent = DialogueAgent()
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
    print({"intent": frames[-1]["intent"], "function": frames[-1]["function"], "slots": frames[-1]["slots"]})


if __name__ == "__main__":
    main()

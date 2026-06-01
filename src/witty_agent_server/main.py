from uvicorn import run
from witty_agent_server.app import create_app


def main() -> None:
    run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

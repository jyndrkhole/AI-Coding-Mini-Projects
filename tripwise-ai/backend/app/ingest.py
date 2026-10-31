"""Embed the travel notebook into persistent Chroma."""

from app.ai.ingestion import ingest_notebook


def main() -> None:
    count = ingest_notebook()
    print(f"Ingested {count} notebook passages into Chroma.")


if __name__ == "__main__":
    main()

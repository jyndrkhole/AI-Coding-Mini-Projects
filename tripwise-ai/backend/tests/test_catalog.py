from app.ai.chunking import chunk_text
from app.ai.host_tools import run_host_tool
from app.ai.retriever import build_where


def test_chunk_text_overlaps():
    chunks = chunk_text("abcdefghij", size=4, overlap=1)
    assert chunks == ["abcd", "defg", "ghij"]


def test_short_text_is_one_chunk():
    assert chunk_text("  hello   world ", size=50, overlap=10) == ["hello world"]


def test_build_where_combines_filters():
    where = build_where(destination="Manali", season="July")
    assert where == {"$and": [{"destination": "Manali"}, {"season": "July"}]}


def test_stay_share_tool_uses_python():
    result = run_host_tool("calculate_stay_share", {"room_price_per_night": 3000, "nights": 3, "people": 4})
    assert result["rooms_needed"] == 2
    assert result["stay_share"] == 4500

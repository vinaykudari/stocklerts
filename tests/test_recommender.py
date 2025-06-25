import importlib
from app.recommendations import daily_recommender as dr


def test_parse_recommendations_handles_think_block():
    text = """<think>some reasoning</think>\nAAPL - reason one\nMSFT - reason two\n"""
    recs = dr.parse_recommendations(text)
    assert recs == [
        {'symbol': 'AAPL', 'reason': 'reason one'},
        {'symbol': 'MSFT', 'reason': 'reason two'},
    ]


def test_parse_best_performers_simple():
    text = """AAPL - great earnings - 5.2%\nMSFT 4.1% - strong sales"""
    recs = dr.parse_best_performers(text)
    assert recs == [
        {'symbol': 'AAPL', 'reason': 'great earnings', 'pct': 5.2},
        {'symbol': 'MSFT', 'reason': 'strong sales', 'pct': 4.1},
    ]


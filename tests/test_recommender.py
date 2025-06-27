import importlib
from app.recommendations import daily_recommender as dr


def test_parse_recommendations_handles_think_block():
    text = """<think>some reasoning</think>\nAAPL - reason one\nMSFT - reason two\n"""
    recs = dr.parse_recommendations(text)
    assert recs == [
        {'symbol': 'AAPL', 'reason': 'reason one'},
        {'symbol': 'MSFT', 'reason': 'reason two'},
    ]



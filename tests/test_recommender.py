import importlib
from app.recommendations import daily_recommender as dr


def test_parse_recommendations_handles_think_block():
    text = (
        "<think>some reasoning</think>\n"
        "$AAPL | reason one | +2% | Low\n"
        "$MSFT | reason two | +3% | Medium\n"
    )
    recs = dr.parse_recommendations(text)
    assert recs == [
        {
            'symbol': 'AAPL',
            'catalyst': 'reason one',
            'target': '2%',
            'risk': 'Low',
        },
        {
            'symbol': 'MSFT',
            'catalyst': 'reason two',
            'target': '3%',
            'risk': 'Medium',
        },
    ]



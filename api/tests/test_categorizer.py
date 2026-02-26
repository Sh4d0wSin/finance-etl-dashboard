from app.categorizer import categorize


def test_categorize_groceries():
    assert categorize("Aldi Süd Berlin") == "Groceries"
    assert categorize("LIDL SAGT DANKE") == "Groceries"


def test_categorize_transport():
    assert categorize("UBER *TRIP") == "Transport"
    assert categorize("Bolt ride") == "Transport"


def test_categorize_subscriptions():
    assert categorize("Netflix.com") == "Subscriptions"
    assert categorize("SPOTIFY AB") == "Subscriptions"


def test_categorize_unknown_returns_uncategorized():
    assert categorize("Random Shop XYZ") == "Uncategorized"
    assert categorize("") == "Uncategorized"

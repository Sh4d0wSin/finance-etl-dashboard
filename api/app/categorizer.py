import re

RULES = [
    (r"\b(uber|bolt|lyft|taxi)\b", "Transport"),
    (r"\b(aldi|lidl|rewe|edeka|walmart|whole foods)\b", "Groceries"),
    (r"\b(netflix|spotify|prime)\b", "Subscriptions"),
    (r"\b(starbucks|coffee)\b", "Coffee"),
    (r"\b(mcdonald|burger king|kfc|subway)\b", "Fast Food"),
]

def categorize(description: str) -> str:
    d = (description or "").lower()
    for pattern, cat in RULES:
        if re.search(pattern, d):
            return cat
    return "Uncategorized"

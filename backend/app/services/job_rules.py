"""Shared rules for job search: experience parsing, city spellings, monthly pay."""
import re

# Search for a city also finds the common alternative spellings people type
CITY_ALIASES: dict[str, list[str]] = {
    "bengaluru": ["bengaluru", "bangalore", "bengalore", "banglore", "bengalooru", "blr"],
    "gurugram": ["gurugram", "gurgaon"],
    "mumbai": ["mumbai", "bombay", "navi mumbai"],
    "chennai": ["chennai", "madras"],
    "kolkata": ["kolkata", "calcutta"],
    "mysuru": ["mysuru", "mysore"],
    "mangaluru": ["mangaluru", "mangalore"],
    "hubballi": ["hubballi", "hubli"],
    "belagavi": ["belagavi", "belgaum"],
    "thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
    "kochi": ["kochi", "cochin"],
    "puducherry": ["puducherry", "pondicherry"],
    "vadodara": ["vadodara", "baroda"],
    "delhi": ["delhi", "new delhi"],
}

# Experience filter buckets: (lowest, highest) years a job may ask for
EXPERIENCE_BUCKETS: dict[str, tuple[float, float | None]] = {
    "fresher": (0, 0),   # open to people with no experience
    "1-3": (1, 3),
    "3-5": (3, 5),
    "5-8": (5, 8),
    "8+": (8, None),
}


def city_terms(city: str) -> list[str]:
    """All spellings to match for a searched city (or just the text itself)."""
    key = city.strip().lower()
    for names in CITY_ALIASES.values():
        if key in names:
            return names
    return [key]


def parse_min_years(text: str | None) -> float | None:
    """Minimum years of experience a job asks for: 'Fresher' -> 0, '2-4 years' -> 2, '5+' -> 5."""
    if not text:
        return None
    t = text.lower()
    if re.search(r"fresher|entry|no experience|trainee|intern", t):
        return 0.0
    m = re.search(r"\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None

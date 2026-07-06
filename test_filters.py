"""Filter engine tests. Run: python test_filters.py"""
from agent.filters import compile_targets, evaluate, extract_sizes
from agent.models import Listing

CFG = {
    "targets": [
        {"name": "Trek 720", "pattern": r"\btrek\b.{0,40}\b720\b(?!\d)"},
        {"name": "Bridgestone T-700", "pattern": r"\bt[-\s]?700\b(?!c)"},
        {"name": "Bridgestone 400", "pattern": r"\bbridgestone\b.{0,40}\b400\b(?!\d)"},
        {"name": "Miyata 1000", "pattern": r"\bmiyata\b.{0,40}\b1000\s?(lt)?\b"},
    ],
    "sizing": {"cm_values": [55, 56, 57], "inch_values": ["22", "22.5"],
               "unknown_size": "notify"},
    "exclusions": ["carbon", "7200", "fixie", "single speed"],
}
T = compile_targets(CFG)


def L(title, desc=""):
    return Listing(source="test", title=title, url=f"http://x/{hash(title+desc)}",
                   description=desc)


cases = [
    # (title, description, expected_model_or_None, expected_size_or_None)
    ("1984 Trek 720 touring bike 56cm", "", "Trek 720", "56cm"),
    ("Trek 720 frame", "measures 22.5 inches center to top", "Trek 720", '22.5"'),
    ("Trek 7200 hybrid", "", None, None),                       # exclusion + regex
    ("Trek 720 58cm", "", None, None),                          # wrong size stated
    ("Trek 720, great shape", "no size given", "Trek 720", "unknown"),
    ("Bridgestone T-700 vintage", "size 56", "Bridgestone T-700", "56cm"),
    ("Bridgestone T700", "", "Bridgestone T-700", "unknown"),
    ("Road bike with 700c wheels", "", None, None),             # 700c must not hit T-700
    ("Bridgestone 400 road bike", "57 cm frame", "Bridgestone 400", "57cm"),
    ("Bridgestone 4000 something", "", None, None),
    ("Miyata 1000 LT touring", '22" frame', "Miyata 1000", '22"'),
    ("Miyata 1000 carbon fork upgrade", "", None, None),        # exclusion
    ("Miyata One", "", None, None),
    ("Trek 720 single speed conversion", "", None, None),       # exclusion
]

failed = 0
for title, desc, want_model, want_size in cases:
    m = evaluate(L(title, desc), CFG, T)
    got_model = m.model if m else None
    got_size = m.size if m else None
    ok = got_model == want_model and got_size == want_size
    if not ok:
        failed += 1
    print(f"{'PASS' if ok else 'FAIL'}: {title!r} -> {got_model}, {got_size}"
          + ("" if ok else f"  (wanted {want_model}, {want_size})"))

# Size extractor edge cases
assert extract_sizes("22.5 inch") == ([], ["22.5"]), "22.5 must not match as 22"
assert extract_sizes("56cm c-t") == (["56"], [])
assert extract_sizes("sz 56, nice") == (["56"], [])
assert extract_sizes("bought in 1956") == ([], []), "years must not match"
print("size extractor edge cases: PASS")

print(f"\n{len(cases) - failed}/{len(cases)} cases passed")
exit(1 if failed else 0)

import re
from pathlib import Path

import amortsched

PACKAGE = Path(amortsched.__file__).parent
ROUNDING_OWNER = PACKAGE / "core" / "money.py"
ROUNDING = re.compile(r"\.quantize\(|\bROUND_[A-Z_]+\b|\bround\(")


def test_only_the_money_module_rounds():
    offenders = [
        f"{path.relative_to(PACKAGE)}:{number}: {line.strip()}"
        for path in sorted(PACKAGE.rglob("*.py"))
        if path != ROUNDING_OWNER
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if ROUNDING.search(line)
    ]
    assert offenders == [], "Round through amortsched.core.money:\n" + "\n".join(offenders)

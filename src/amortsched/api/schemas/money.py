from decimal import Decimal
from typing import Annotated

from pydantic import Field

MoneyInput = Annotated[Decimal, Field(decimal_places=2)]

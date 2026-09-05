"""Strict SI-base physical units system — INTENTIONALLY EMPTY in Stage 0.

Per the Stage 0 prompt: the module may exist but must hold zero domain logic.
Stage 1 Commit 1A builds the typed quantities (`Quantity`, `Farad`, `Ohm`,
`Volt`, ...) and boundary converters here, with the test proving unit strings
such as "10MHz" never reach storage. Nothing may import names from this
module until then.
"""

__all__: list[str] = []

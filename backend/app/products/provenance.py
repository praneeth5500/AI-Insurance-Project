"""Where a product fact came from.

docs/06_RECOMMENDATION_ENGINE.md section 3: every product record must be
labelled. The label travels with the product all the way to the screen, so a
demo product can never be mistaken for a verified one.
"""

from __future__ import annotations

from typing import Literal

#: SYNTHETIC        — invented for development and UX testing. Never a fact.
#: MANUALLY_VERIFIED — checked against source documents and versioned.
#: PARTNER_API       — received from an approved integration.
SourceType = Literal["SYNTHETIC", "MANUALLY_VERIFIED", "PARTNER_API"]

SYNTHETIC: SourceType = "SYNTHETIC"

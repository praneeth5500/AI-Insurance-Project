"""The synthetic health product catalogue.

**Everything here is invented.** The insurers do not exist and the products do
not exist. docs/11_BUILD_PLAN.md Phase 5 says "Use synthetic products", and
docs/00_README.md's prototype truth rule requires that such data is never
allowed to look verified — so every insurer name ends in "(demo)" and the
source type travels with the product all the way to the screen.

What changed in Phase 9: these products used to carry hand-written fit labels
("co-pay: STRONG"). They now carry **facts** — the co-pay percentage, the
waiting period in months, whether room charges are capped — and the engine
works the labels out for a particular person. A product no longer has an
opinion about whether it suits you; it states what it does, and
`app.matching` decides what that means for the reader.

Three rules were followed while writing this file:

1. **No real insurer or product name.** Every name is obviously fictional, so
   a screenshot of this build cannot be mistaken for a real comparison.
2. **No premium.** CLAUDE.md is unconditional: never invent a premium. These
   products carry no price at all, and the budget dimension reports "not
   enough verified data" rather than guessing — which is exactly the
   behaviour docs/06_RECOMMENDATION_ENGINE.md section 8 asks for.
3. **No claim outcomes and no eligibility promises about real people.** The
   entry ages and family compositions here are fixture values that exercise
   the eligibility rules; they describe nothing that exists.

Real products arrive through the Phase 8 importer, behind provenance and
versioning, and reach the same engine through the same provider interface.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.products.facts import HealthFacts
from app.products.provenance import SYNTHETIC, SourceType

CATALOGUE_VERSION = "synthetic-health-002"

#: Rupee amounts, written out so the fixtures stay readable.
LAKH = 100_000


class SyntheticProduct(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    insurer_name: str
    product_name: str
    source_type: SourceType = SYNTHETIC
    catalogue_version: str = CATALOGUE_VERSION
    facts: HealthFacts
    #: The single most important thing to be aware of. Every product has one:
    #: docs/02_UX_UI_SPEC.md rule 4 — trust requires discussing disadvantages.
    #: Authored rather than derived, because "what would surprise someone
    #: about this policy" is an editorial judgement, not a computation.
    watch_out: str


#: Ten demo products, so the "5 primary + see 5 more" result set is real
#: (docs/01_PRODUCT_SPEC.md section 2.5).
#:
#: The spread is deliberate. Between them these products exercise every branch
#: the engine has: an age-restricted product, two that only support a single
#: applicant, one that cannot be bought by a single applicant, one whose
#: co-pay only starts above a certain age, and one with a fact missing
#: entirely so the "not enough verified data" path is always live.
PRODUCTS: tuple[SyntheticProduct, ...] = (
    SyntheticProduct(
        id="sp_meridian_core",
        insurer_name="Meridian Mutual (demo)",
        product_name="Core Health",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=65,
            supported_compositions=("just_me", "me_spouse", "me_family"),
            sum_insured_options_inr=(5 * LAKH, 10 * LAKH, 25 * LAKH),
            max_children=3,
            restoration=True,
            copay_percent=0,
            ped_waiting_months=24,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="CAPPED_PERCENT",
            room_cap_percent=1,
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=7500,
            sublimit_count=0,
            notable_exclusion_count=3,
        ),
        watch_out=(
            "Room charges are capped, so a more expensive room can reduce what is paid on the "
            "whole bill."
        ),
    ),
    SyntheticProduct(
        id="sp_northgate_value",
        insurer_name="Northgate Assurance (demo)",
        product_name="Value Shield",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=60,
            supported_compositions=("just_me", "me_spouse"),
            sum_insured_options_inr=(3 * LAKH, 5 * LAKH),
            restoration=False,
            copay_percent=20,
            ped_waiting_months=48,
            specific_treatment_waiting_months=36,
            initial_waiting_days=30,
            room_rule="CAPPED_PERCENT",
            room_cap_percent=1,
            cashless_scope="NETWORK_ONLY",
            network_hospital_count=4200,
            sublimit_count=5,
            sublimit_treatments=("cataract", "joint replacement", "hernia"),
            notable_exclusion_count=8,
        ),
        watch_out=(
            "A co-pay applies to every claim, so a low premium can cost more when you actually "
            "claim."
        ),
    ),
    SyntheticProduct(
        id="sp_harbourline_family",
        insurer_name="Harbourline Health (demo)",
        product_name="Family First",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=65,
            supported_compositions=("me_spouse", "me_family"),
            sum_insured_options_inr=(10 * LAKH, 15 * LAKH, 25 * LAKH),
            max_children=4,
            restoration=True,
            copay_percent=0,
            ped_waiting_months=36,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="ANY_ROOM",
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=9000,
            sublimit_count=1,
            sublimit_treatments=("cataract",),
            notable_exclusion_count=4,
        ),
        watch_out=(
            "Cover is shared, so one large claim can leave less available for everyone else "
            "that year."
        ),
    ),
    SyntheticProduct(
        id="sp_alderwood_essential",
        insurer_name="Alderwood Cover (demo)",
        product_name="Essential Care",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=55,
            supported_compositions=("just_me",),
            sum_insured_options_inr=(3 * LAKH, 5 * LAKH),
            restoration=False,
            copay_percent=0,
            ped_waiting_months=12,
            specific_treatment_waiting_months=12,
            initial_waiting_days=30,
            room_rule="SINGLE_PRIVATE",
            cashless_scope="NETWORK_ONLY",
            network_hospital_count=6100,
            sublimit_count=3,
            sublimit_treatments=("cataract", "hernia"),
            notable_exclusion_count=3,
        ),
        watch_out="The cover amount is lower, so a long hospital stay could use most of it.",
    ),
    SyntheticProduct(
        id="sp_beacon_wide",
        insurer_name="Beacon Life (demo)",
        product_name="Wide Cover",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=70,
            supported_compositions=("just_me", "me_spouse", "me_family", "my_parents"),
            sum_insured_options_inr=(25 * LAKH, 50 * LAKH, 100 * LAKH),
            max_children=3,
            restoration=True,
            copay_percent=0,
            ped_waiting_months=48,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="ANY_ROOM",
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=8200,
            sublimit_count=0,
            notable_exclusion_count=6,
        ),
        watch_out="Existing conditions wait longer here than on most of the other options shown.",
    ),
    SyntheticProduct(
        id="sp_stillwater_flex",
        insurer_name="Stillwater Mutual (demo)",
        product_name="Flexible Plan",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=65,
            supported_compositions=("just_me", "me_spouse", "me_family"),
            sum_insured_options_inr=(5 * LAKH, 10 * LAKH, 20 * LAKH),
            max_children=2,
            restoration=False,
            copay_percent=10,
            copay_applies_above_age=60,
            ped_waiting_months=24,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="CAPPED_AMOUNT",
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=3400,
            sublimit_count=2,
            sublimit_treatments=("cataract",),
            notable_exclusion_count=4,
        ),
        watch_out=(
            "A co-pay starts applying above a set age, which can change what you pay later on."
        ),
    ),
    SyntheticProduct(
        id="sp_kestrel_secure",
        insurer_name="Kestrel Insurance (demo)",
        product_name="Secure Health",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=65,
            supported_compositions=("just_me", "me_spouse"),
            sum_insured_options_inr=(5 * LAKH, 10 * LAKH),
            restoration=False,
            copay_percent=0,
            ped_waiting_months=36,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="SINGLE_PRIVATE",
            cashless_scope="NETWORK_ONLY",
            network_hospital_count=2100,
            sublimit_count=2,
            sublimit_treatments=("cataract",),
            notable_exclusion_count=4,
        ),
        watch_out=(
            "Cashless treatment only works inside the network, so an out-of-network hospital "
            "means paying first and claiming later."
        ),
    ),
    SyntheticProduct(
        id="sp_orchard_senior",
        insurer_name="Orchard Assurance (demo)",
        product_name="Senior Care",
        facts=HealthFacts(
            entry_age_min=55,
            entry_age_max=80,
            supported_compositions=("just_me", "my_parents"),
            sum_insured_options_inr=(5 * LAKH, 10 * LAKH),
            restoration=False,
            copay_percent=20,
            ped_waiting_months=24,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="CAPPED_PERCENT",
            room_cap_percent=2,
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=8800,
            sublimit_count=4,
            sublimit_treatments=("cataract", "joint replacement"),
            notable_exclusion_count=7,
        ),
        watch_out="A co-pay applies to every claim, which adds up if claims are frequent.",
    ),
    SyntheticProduct(
        id="sp_verdant_balanced",
        insurer_name="Verdant Health (demo)",
        product_name="Balanced Cover",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=65,
            supported_compositions=("just_me", "me_spouse", "me_family"),
            sum_insured_options_inr=(5 * LAKH, 10 * LAKH, 15 * LAKH),
            max_children=3,
            restoration=True,
            copay_percent=0,
            ped_waiting_months=36,
            specific_treatment_waiting_months=24,
            initial_waiting_days=30,
            room_rule="CAPPED_PERCENT",
            room_cap_percent=1,
            cashless_scope="ANY_HOSPITAL",
            network_hospital_count=6800,
            sublimit_count=3,
            sublimit_treatments=("cataract", "hernia"),
            notable_exclusion_count=5,
        ),
        watch_out="Nothing stands out as weak, but nothing stands out as especially strong either.",
    ),
    SyntheticProduct(
        id="sp_lantern_starter",
        insurer_name="Lantern Cover (demo)",
        product_name="Starter Health",
        facts=HealthFacts(
            entry_age_min=18,
            entry_age_max=45,
            supported_compositions=("just_me",),
            sum_insured_options_inr=(2 * LAKH, 3 * LAKH),
            restoration=False,
            copay_percent=0,
            ped_waiting_months=36,
            specific_treatment_waiting_months=36,
            initial_waiting_days=30,
            room_rule="CAPPED_PERCENT",
            room_cap_percent=1,
            cashless_scope="NETWORK_ONLY",
            network_hospital_count=2600,
            sublimit_count=6,
            sublimit_treatments=("cataract", "joint replacement", "hernia"),
            # Deliberately absent. The exclusions dimension reports "not enough
            # verified data" for this product and drops out of the weighting
            # rather than being scored as average
            # (docs/06_RECOMMENDATION_ENGINE.md section 8).
            notable_exclusion_count=None,
        ),
        watch_out=(
            "The cover amount is the lowest here, so it may not stretch far for a serious "
            "hospital stay."
        ),
    ),
)


def all_products() -> tuple[SyntheticProduct, ...]:
    return PRODUCTS


def get_product(product_id: str) -> SyntheticProduct | None:
    return next((product for product in PRODUCTS if product.id == product_id), None)

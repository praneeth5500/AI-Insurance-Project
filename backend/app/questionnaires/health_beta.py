"""The seeded health questionnaire.

**Status: DRAFT.** docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 6 says the
structure of the health questionnaire is decided but the exact wording and
data fields still need a dedicated pass. So this version is marked DRAFT and
every question is drawn from a list the specification already gives:

* fields come only from the candidate inputs in docs/01_PRODUCT_SPEC.md
  section 2.2;
* priorities come only from docs/01_PRODUCT_SPEC.md section 2.3;
* stage names come from docs/01_PRODUCT_SPEC.md section 2.2;
* the "who are you looking to protect" wording and its options are taken
  verbatim from the example screen in docs/02_UX_UI_SPEC.md section 7.

Nothing here asks for detailed medical history — the specification forbids it
by default — and nothing states an insurance fact. Sum-insured brackets are
the user's own target, not a product's terms.

Changing any question means a **new version**, never an edit: a completed
session records the version it was answered against
(docs/04_BACKEND_ARCHITECTURE.md section 9).
"""

from __future__ import annotations

from app.questionnaires.definitions import (
    Condition,
    Option,
    QuestionDefinition,
    QuestionnaireDefinition,
    Stage,
)

HEALTH_BETA_VERSION = "health-beta-draft-001"

STAGES = (
    Stage(key="about-you", label="About you"),
    Stage(key="current-cover", label="Your cover"),
    Stage(key="priorities", label="What matters"),
)

#: Options for "who are you looking to protect?", verbatim from
#: docs/02_UX_UI_SPEC.md section 7.
COVER_FOR_JUST_ME = "just_me"
COVER_FOR_ME_SPOUSE = "me_spouse"
COVER_FOR_ME_FAMILY = "me_family"
COVER_FOR_MY_PARENTS = "my_parents"

PRIORITY_QUESTION_ID = "priorities"
#: Priority keys, from docs/01_PRODUCT_SPEC.md section 2.3.
PRIORITY_KEYS = (
    "lower_premium",
    "low_copay",
    "short_waiting_periods",
    "hospital_flexibility",
    "broad_coverage",
    "fewer_sublimits",
)

QUESTIONS = (
    # ---------------------------------------------------------- About you --
    QuestionDefinition(
        id="applicant_age",
        stage="about-you",
        title="How old are you?",
        input_type="NUMBER",
        data_field="applicant_age",
        analytics_key="question_applicant_age",
        help_text=(
            "Age affects which policies you are eligible for and how they are priced. "
            "We ask for a number, not a date of birth."
        ),
        unit="years",
        min_value=18,
        max_value=99,
    ),
    QuestionDefinition(
        id="pincode",
        stage="about-you",
        title="What's your pincode?",
        description="Where you live affects which options are available to you.",
        input_type="PINCODE",
        data_field="pincode",
        analytics_key="question_pincode",
        help_text=(
            "Availability and hospital networks differ by area. We use your pincode "
            "only to work out which options apply to you."
        ),
    ),
    QuestionDefinition(
        id="broad_health_conditions",
        stage="about-you",
        title="Does anyone to be covered have an ongoing health condition?",
        description="A yes or no is enough. We don't ask what the condition is.",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="no", label="No"),
            Option(
                value="yes",
                label="Yes",
                description="Some policies wait longer before covering existing conditions",
            ),
            Option(value="prefer_not_to_say", label="I'd rather not say"),
        ),
        data_field="broad_health_conditions",
        analytics_key="question_broad_health_conditions",
        help_text=(
            "Waiting periods for pre-existing conditions are one of the biggest "
            "differences between policies. Knowing only whether one applies lets us "
            "point that out. We never ask for a diagnosis or medical history, and you "
            "can skip this."
        ),
        required=False,
        sensitive=True,
    ),
    # --------------------------------------------------------- Your cover --
    QuestionDefinition(
        id="cover_for",
        stage="current-cover",
        title="Who are you looking to protect?",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value=COVER_FOR_JUST_ME, label="Just me"),
            Option(value=COVER_FOR_ME_SPOUSE, label="Me + spouse"),
            Option(value=COVER_FOR_ME_FAMILY, label="Me + family"),
            Option(value=COVER_FOR_MY_PARENTS, label="My parents"),
        ),
        data_field="cover_for",
        analytics_key="question_cover_for",
        help_text=(
            "Who is covered changes which policies you can take out at all, and how "
            "cover is shared between people."
        ),
    ),
    QuestionDefinition(
        id="spouse_age",
        stage="current-cover",
        title="How old is your spouse?",
        input_type="NUMBER",
        data_field="spouse_age",
        analytics_key="question_spouse_age",
        show_if=Condition(
            field="cover_for",
            operator="IN",
            value=[COVER_FOR_ME_SPOUSE, COVER_FOR_ME_FAMILY],
        ),
        unit="years",
        min_value=18,
        max_value=99,
    ),
    QuestionDefinition(
        id="children_count",
        stage="current-cover",
        title="How many children should be covered?",
        input_type="NUMBER",
        data_field="children_count",
        analytics_key="question_children_count",
        show_if=Condition(field="cover_for", operator="EQUALS", value=COVER_FOR_ME_FAMILY),
        unit="children",
        min_value=1,
        max_value=10,
    ),
    QuestionDefinition(
        id="oldest_parent_age",
        stage="current-cover",
        title="How old is the older parent?",
        input_type="NUMBER",
        data_field="oldest_parent_age",
        analytics_key="question_oldest_parent_age",
        show_if=Condition(field="cover_for", operator="EQUALS", value=COVER_FOR_MY_PARENTS),
        help_text=(
            "Policies for parents often have their own age limits and waiting periods. "
            "The older parent is the one that usually decides what is available."
        ),
        unit="years",
        min_value=18,
        max_value=99,
    ),
    QuestionDefinition(
        id="has_employer_cover",
        stage="current-cover",
        title="Are you covered by an employer health plan?",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="yes", label="Yes"),
            Option(value="no", label="No"),
            Option(value="not_sure", label="I'm not sure"),
        ),
        data_field="has_employer_cover",
        analytics_key="question_has_employer_cover",
        help_text=(
            "Employer cover usually ends when the job does, and often covers less than "
            "people expect. Knowing you have it changes what is worth adding."
        ),
    ),
    QuestionDefinition(
        id="has_personal_cover",
        stage="current-cover",
        title="Do you already have your own health policy?",
        input_type="BOOLEAN",
        data_field="has_personal_cover",
        analytics_key="question_has_personal_cover",
    ),
    QuestionDefinition(
        id="desired_cover",
        stage="current-cover",
        title="How much cover are you aiming for?",
        description="A rough figure is fine. You can change this later.",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="up_to_5l", label="Up to ₹5 lakh"),
            Option(value="5l_to_10l", label="₹5–10 lakh"),
            Option(value="10l_to_25l", label="₹10–25 lakh"),
            Option(value="above_25l", label="More than ₹25 lakh"),
            Option(value="not_sure", label="I'm not sure yet"),
        ),
        data_field="desired_cover",
        analytics_key="question_desired_cover",
        help_text=(
            "This is your own target, not a quote. It helps us show options in the "
            "range you have in mind, and flag where that range may not stretch far."
        ),
    ),
    QuestionDefinition(
        id="approximate_budget",
        stage="current-cover",
        title="Roughly what would you like to spend a year?",
        description="Optional. Leave it blank if you'd rather see the full range.",
        input_type="MONEY",
        data_field="approximate_budget",
        analytics_key="question_approximate_budget",
        required=False,
        help_text=(
            "We use this to show where an option sits against your budget. We never "
            "quote a price from it — premiums come from the insurer, not from us."
        ),
        unit="₹ per year",
        min_value=0,
    ),
    QuestionDefinition(
        id="room_preference",
        stage="current-cover",
        title="What kind of hospital room would you want?",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="shared_is_fine", label="A shared room is fine"),
            Option(value="private_room", label="A private room"),
            Option(value="no_preference", label="No strong preference"),
        ),
        data_field="room_preference",
        analytics_key="question_room_preference",
        help_text=(
            "Many policies cap what they pay towards a room. If the cap is below the "
            "room you choose, you can end up paying a share of the whole bill."
        ),
    ),
    QuestionDefinition(
        id="copay_tolerance",
        stage="current-cover",
        title="Would you accept paying a share of each claim?",
        description="A co-pay lowers the premium but means you pay part of every claim.",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="prefer_none", label="I'd rather not"),
            Option(value="small_share_ok", label="A small share is fine"),
            Option(value="not_sure", label="I'm not sure"),
        ),
        data_field="copay_tolerance",
        analytics_key="question_copay_tolerance",
    ),
    QuestionDefinition(
        id="waiting_period_sensitivity",
        stage="current-cover",
        title="How soon do you need cover to start fully?",
        description="Most policies wait before covering some treatments.",
        input_type="SINGLE_CHOICE",
        options=(
            Option(value="as_soon_as_possible", label="As soon as possible"),
            Option(value="somewhat_important", label="It matters, but I can wait"),
            Option(value="not_a_concern", label="Not a concern"),
        ),
        data_field="waiting_period_sensitivity",
        analytics_key="question_waiting_period_sensitivity",
    ),
    # ------------------------------------------------------- What matters --
    QuestionDefinition(
        id=PRIORITY_QUESTION_ID,
        stage="priorities",
        title="Choose up to 3 things that matter most.",
        description="We'll use these to explain why an option fits you.",
        input_type="MULTI_CHOICE",
        options=(
            Option(value="lower_premium", label="Lower premium"),
            Option(value="low_copay", label="Low co-pay"),
            Option(value="short_waiting_periods", label="Short waiting periods"),
            Option(value="hospital_flexibility", label="Hospital flexibility"),
            Option(value="broad_coverage", label="Broad coverage"),
            Option(value="fewer_sublimits", label="Fewer sub-limits"),
        ),
        data_field="priorities",
        analytics_key="question_priorities",
        max_selections=3,
        help_text=(
            "There is no single best policy — every option trades one thing off "
            "against another. Telling us what matters lets us show you where each "
            "option helps and where it costs you. You can change these later."
        ),
    ),
)

HEALTH_BETA = QuestionnaireDefinition(
    domain="HEALTH",
    version=HEALTH_BETA_VERSION,
    status="DRAFT",
    stages=STAGES,
    questions=QUESTIONS,
)

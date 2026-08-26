"""Import every mapped model, so the SQLAlchemy registry is complete.

A mapper is only configured once its module has been imported. The API gets
this for free — its routers pull in every domain — but the worker imports only
what it directly uses, and a foreign key pointing at a table whose model was
never imported fails at *runtime*, on the first query, with an error that
names the column rather than the missing import.

That is what happened when the worker first ran the extraction pipeline:
`uploaded_policies.user_id` could not find `users`. Rather than adding one
import to the worker and waiting for the next occurrence, every entry point
now imports this module, and there is one list to keep current instead of
several.

`migrations/env.py` needs the same list for autogenerate, so it uses this too.
"""

from __future__ import annotations

from app.audit import models as audit_models
from app.auth import models as auth_models
from app.extraction import models as extraction_models
from app.jobs import models as job_models
from app.policies import models as policy_models
from app.pricing import models as pricing_models
from app.products import models as product_models
from app.qa import models as qa_models
from app.questionnaires import models as questionnaire_models
from app.recommendations import models as recommendation_models
from app.users import models as user_models

#: Referenced so linters keep the imports, and so the list is visible as data.
MODEL_MODULES = (
    audit_models,
    auth_models,
    extraction_models,
    job_models,
    policy_models,
    pricing_models,
    product_models,
    qa_models,
    questionnaire_models,
    recommendation_models,
    user_models,
)

__all__ = ["MODEL_MODULES"]

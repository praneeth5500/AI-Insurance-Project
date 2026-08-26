"""The policy decoder: turning stored facts and clauses into a readable report.

This is the explanation layer (docs/07_POLICY_DECODER_AI.md section 3). It is
composed at render time and never stored, so an explanation cannot outlive or
contradict the fact it explains.
"""

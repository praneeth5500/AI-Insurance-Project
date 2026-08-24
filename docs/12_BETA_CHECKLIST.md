# Friends & Family Beta Checklist

## Product scope

- [ ] Health recommendation flow is the only full recommendation domain enabled initially unless Motor is genuinely ready
- [ ] Existing policy decoder enabled
- [ ] Claims readiness limited to explanation + checklist
- [ ] No fake checkout
- [ ] No unsupported product claims

## Access

- [ ] Email allowlist enabled
- [ ] Magic link works
- [ ] Sessions expire/revoke correctly
- [ ] Non-allowlisted users blocked

## Recommendation

- [ ] Hard eligibility tested
- [ ] User Top 3 priorities work
- [ ] Priority changes recalculate deterministically
- [ ] 5 primary matches render correctly
- [ ] See 5 more works
- [ ] Compare max 3
- [ ] No visible overall numeric fit score
- [ ] Each match has why + watch-out
- [ ] Unknown critical data is not hidden
- [ ] Historical run saved

## Product data

- [ ] Every beta product is SYNTHETIC, MANUALLY_VERIFIED, or PARTNER_API
- [ ] Demo/synthetic products clearly labeled
- [ ] Real products have source/version
- [ ] Critical real-product facts have verified timestamp
- [ ] Stale critical records excluded

## Premium

- [ ] Every displayed premium has pricing state
- [ ] Every premium has source
- [ ] Timestamp shown/available
- [ ] Taxes/fees state captured if known
- [ ] Indicative not described as final
- [ ] No invented range
- [ ] No misleading "from" personalized price

## Upload

- [ ] PDF works
- [ ] Scanned PDF works or fails clearly
- [ ] Images supported as designed
- [ ] File limit enforced
- [ ] Invalid type rejected
- [ ] Password-protected PDF handled
- [ ] Private storage verified
- [ ] Cross-user access test passes

## Decoder

- [ ] Every important fact links to source where possible
- [ ] Not-found state visible
- [ ] Conflicting/low-confidence state visible
- [ ] Simplification does not hide technical term
- [ ] Examples clearly labeled as examples

## Q&A

- [ ] Answers grounded in policy
- [ ] Citations correct in golden tests
- [ ] Missing information produces uncertainty
- [ ] No claim guarantee
- [ ] AI outage handled

## Privacy/security

- [ ] No public S3
- [ ] No raw documents in logs
- [ ] No sensitive health answers in analytics
- [ ] Delete policy works
- [ ] Sign out works
- [ ] Secrets not committed
- [ ] Production-beta DB separate from local/staging

## UX

- [ ] Mobile questionnaire tested
- [ ] Mobile comparison tested
- [ ] Decoder desktop split tested
- [ ] Decoder mobile tested
- [ ] Keyboard navigation basics work
- [ ] Errors are readable
- [ ] Loading states exist
- [ ] Empty states exist
- [ ] No dead buttons

## Analytics

- [ ] recommendation_started
- [ ] questionnaire_completed
- [ ] recommendation_generated
- [ ] priority_changed
- [ ] comparison_viewed
- [ ] match_opened
- [ ] policy_upload_completed
- [ ] policy_processing_completed
- [ ] policy_question_asked
- [ ] citation_opened
- [ ] feedback_submitted

## Founder review

- [ ] I can explain exactly which data produced each recommendation
- [ ] I can explain where every displayed policy fact came from
- [ ] I know which parts are prototype logic
- [ ] I know which parts use verified real data
- [ ] I have personally tested the full flow on mobile
- [ ] I have asked at least a few users to complete it without my help

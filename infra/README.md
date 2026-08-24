# Infrastructure

Empty until Phase 16.

Deployment is specified in `docs/09_AWS_DEPLOYMENT.md`: managed Next.js
hosting for the frontend, AWS container hosting for the API and worker,
managed PostgreSQL, a private S3 bucket, SQS, and CloudWatch — with an AWS
India region preferred for the beta.

Nothing is committed here yet because provisioning before there is an
application to deploy would lock in vendor choices that
`docs/13_DECISIONS_AND_OPEN_ITEMS.md` deliberately leaves open.

**Never commit** credentials, connection strings, bucket names with account
identifiers, or `.tfstate`. Secrets belong in a secret manager.

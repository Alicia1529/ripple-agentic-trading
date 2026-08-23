# Runtime storage options for D15

Research date: 2026-08-22. This note compares managed storage stacks against the semantics in [D15](../DECISIONS.md#d15--runtime-state-audit-artifacts-and-git-use-separate-storage-responsibilities). It uses vendor and PostgreSQL primary documentation only. It does not provision or benchmark anything.

## Provisional candidate

Evaluate **Amazon Aurora PostgreSQL Serverless v2 + the RDS Data API** for transactional runtime truth, and a separate **Amazon S3 bucket with Versioning and Object Lock** for immutable audit bundles.

This is the smallest responsible candidate found in the documentation review, rather than the service with the lowest theoretical request bill:

- PostgreSQL directly supplies transactions, unique constraints, conditional `UPDATE ... WHERE ... RETURNING`, row locks, and schema-level enforcement. PostgreSQL documents both [unique constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-UNIQUE-CONSTRAINTS) and [conditional updates with returned rows](https://www.postgresql.org/docs/current/sql-update.html). Aurora's Data API exposes explicit `BeginTransaction`, `CommitTransaction`, and `RollbackTransaction` operations over HTTPS; an idle Data API transaction is automatically rolled back after three minutes, so Ripple must keep correctness transactions short. [AWS Data API operations](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html), [AWS transaction example and timeout](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.calling.cli.html)
- A Serverless v2 writer can be configured with a minimum of 0 ACUs. While paused, its instance charge is zero, although storage and other cluster charges continue. Typical resume is approximately 15 seconds and can be 30 seconds or longer after deep sleep, which is acceptable for Ripple's scheduled, non-high-frequency workload but must be included in runner timeouts. [AWS auto-pause behavior](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html), [AWS Aurora pricing model](https://aws.amazon.com/rds/aurora/pricing/)
- Data API avoids opening a database port to GitHub-hosted runners. The workflow can exchange GitHub's OIDC token for a short-lived AWS role, then use narrowly scoped IAM permissions for Data API and S3. The database credential remains in AWS Secrets Manager and is referenced by ARN, not copied into GitHub. [GitHub OIDC overview](https://docs.github.com/en/actions/concepts/security/openid-connect), [official AWS credentials action](https://github.com/aws-actions/configure-aws-credentials), [AWS Data API authorization](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.access.html)
- S3 Object Lock uses a WORM model and works on individual object versions. Governance mode can be bypassed only by a principal with the special bypass permission; compliance mode cannot be shortened or bypassed even by the account root user. [AWS Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)

No vendor is selected until the hands-on proofs at the end of this note pass. In particular, `0 ACU`, Data API support, and the desired Aurora PostgreSQL engine version must be checked together in the deployment Region; AWS documents that zero-ACU support depends on engine version. A secure PostgreSQL wire-protocol path for logical export is also unresolved and is not supplied by the Data API.

## D15 mapping

| Required behavior | Minimal implementation | Enforcement point |
| --- | --- | --- |
| Immutable `OrderPlan` | Insert once; unique `order_plan_id`; application role has no ordinary update/delete path for published plans | PostgreSQL constraint plus role/trigger tests |
| Append-only `ExecutionEvent` | Insert a new event row; unique `event_id`; foreign key to plan; never rewrite plan state | PostgreSQL constraints and write role |
| Atomic plan/event/risk/reconciliation changes | One short Data API transaction, explicitly committed or rolled back | Aurora PostgreSQL transaction |
| Duplicate-order prevention | Unique `order_id` and unique broker `ref_id`/idempotency key where present | PostgreSQL unique constraints |
| Conditional state transition | `UPDATE ... WHERE current_version = :expected AND state = :allowed RETURNING ...`; zero rows means fail closed | PostgreSQL statement atomicity |
| Cross-runner lease | One lease row per account/plan, acquired or renewed by conditional update; increment a fencing token on every acquisition and require the current token on every protected write | PostgreSQL transaction and unique lease key |
| Audit reference | Store object URI, S3 version ID, SHA-256, size, and media type in the same transaction as the referencing runtime fact | PostgreSQL record plus application hash verification |
| Immutable audit bundle | Content-addressed object key; bucket Versioning; default Object Lock retention; runner can create/read but cannot delete or bypass retention | S3 bucket policy, IAM, and Object Lock |
| Runtime recovery | Continuous Aurora backup with 35-day PITR; periodic manual snapshot for longer recovery needs | Aurora backup configuration |
| Export | Snapshot export to S3; vendor-neutral logical export remains an unresolved requirement | Aurora export job now; separately designed PostgreSQL wire path before selection |

The lease must use a **fencing token**, not expiry alone. After a stalled runner's lease expires, that old process may resume; requiring the newest monotonically increasing token on every protected write prevents it from acting as the owner. PostgreSQL row locks block conflicting row updates only until the transaction ends, so a durable lease row is the correct cross-process primitive rather than a session advisory lock. [PostgreSQL explicit and row locking](https://www.postgresql.org/docs/current/explicit-locking.html)

## Backup, export, and retention baseline

Start with the following explicit baseline and revisit it before live money:

1. Configure Aurora automated backup retention to **35 days**. Aurora backups are continuous and incremental, and the service supports retention from 1–35 days. [AWS Aurora backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Backups.html)
2. Take a monthly manual snapshot and retain twelve months during Phase 0/1. Manual snapshots do not expire automatically. This is a project policy recommendation, not a claim that twelve months satisfies a legal requirement.
3. Export a snapshot to a dedicated backup prefix in S3 after each schema milestone. AWS supports exporting all or selected databases, schemas, or tables from Aurora snapshots without affecting the active cluster. The export is useful evidence and an extraction path, but it is not a substitute for proving a logical PostgreSQL restore. [AWS snapshot export](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-export-snapshot.html)
4. Before vendor selection, design and test a narrowly scoped PostgreSQL wire-protocol path for `pg_dump --format=custom`; the Data API cannot run `pg_dump`. That may require a protected VPC job or another network component and must be included in the cost and threat model. Until then, snapshot export is not a vendor-neutral recovery proof. A resulting dump must be restored into a fresh database, because a backup that has never restored is not yet evidence of recoverability. [PostgreSQL `pg_dump`](https://www.postgresql.org/docs/current/app-pgdump.html)
5. Put audit bundles in a bucket with Versioning and Object Lock enabled. Begin with **governance-mode retention for 400 days**, deny `s3:DeleteObjectVersion` and `s3:BypassGovernanceRetention` to all runner roles, and keep compliance mode off until Alicia deliberately accepts its irreversibility. The 400-day value is an operational starting point, not legal advice.
6. Keep objects in S3 Standard initially. At Ripple's expected volume, lifecycle complexity is unlikely to save meaningful money. Add a transition rule only after measured object volume justifies it; retention prevents deletion before its deadline even if a lifecycle rule otherwise matches.

Database backups and audit bundles serve different purposes. Aurora PITR/snapshots recover operational state; the locked S3 bucket preserves the exact evidence referenced by that state. Neither replaces the other.

## GitHub Actions access boundary

Create one GitHub OIDC provider and separate IAM roles for migration/administration and scheduled runtime execution. Restrict the runtime role's trust policy to the immutable repository identity plus the protected GitHub Environment used for live runs. GitHub documents that OIDC lets workflows obtain short-lived cloud credentials instead of storing a long-lived cloud secret. [GitHub AWS OIDC guide](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)

The runtime role should have only:

- the five required Data API statement/transaction actions on one cluster ARN;
- access to exactly one database secret ARN;
- `s3:PutObject`, `s3:GetObject`, and the minimum version/retention reads on one audit prefix;
- no S3 delete, retention-bypass, bucket-policy, schema-migration, snapshot-delete, or IAM administration permissions.

The migration role owns DDL. A separate backup role owns snapshot export and retention. The unresolved logical-export path needs its own least-privilege identity once its network design is chosen. This separation keeps the day-to-day runner unable to weaken the evidence store it writes.

## Alternatives considered

| Stack | D15 fit | Cost/operations shape | Decision |
| --- | --- | --- | --- |
| **Aurora PostgreSQL Serverless v2 + Data API + S3 Object Lock** | Native relational constraints and SQL transactions; durable lease rows; WORM/versioned objects; clean OIDC-to-IAM runtime path | Scale-to-zero compute with cold-start latency; storage, I/O, Data API, Secrets Manager, and backup charges remain; logical export still needs a protected database network path | **Leading Phase 0 proof candidate; not selected** |
| **DynamoDB on-demand + S3 Object Lock** | ACID multi-item transactions, conditional writes, primary-key uniqueness, distributed-lock patterns, PITR/export, and the same OIDC/IAM boundary | Lowest idle operations burden and pay-per-request billing | Economically smallest, but reject as default because non-key uniqueness, immutability, relationships, and query shapes become custom application protocols |
| **Google Cloud SQL for PostgreSQL + Cloud Storage retention lock** | Standard PostgreSQL semantics; Cloud Storage offers versioning and retention locks; GitHub OIDC can use Workload Identity Federation | Coherent single-provider alternative, but Cloud SQL compute is continuously provisioned; shared-core `db-f1-micro`/`db-g1-small` is documented for low-cost test/development and has no SLA | Keep as fallback if Aurora/Data API compatibility or AWS account constraints fail |

### Why not DynamoDB by default

DynamoDB transactions are ACID and can combine `Put`, `Update`, `Delete`, and `ConditionCheck` actions as one all-or-nothing request. Conditional writes and a dedicated lock item can implement a lease, and on-demand mode charges per request without capacity planning. [AWS DynamoDB transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html), [AWS conditional updates](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html), [AWS concurrency patterns](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices_ImplementingVersionControl.html), [AWS DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/)

However, DynamoDB guarantees uniqueness only for a table's primary key. AWS's documented secondary-uniqueness pattern creates extra guard items and maintains them transactionally; that makes an application convention carry work that PostgreSQL enforces declaratively. [AWS unique-constraint simulation](https://aws.amazon.com/blogs/database/simulating-amazon-dynamodb-unique-constraints-using-transactions/). DynamoDB also limits a transaction to 100 unique items and 4 MB in one account and Region. [AWS DynamoDB transaction constraints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html#limits-dynamodb-transactions)

PITR is fully managed for up to 35 days and a table can be exported to S3 from a restorable point. [AWS DynamoDB PITR](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html), [AWS DynamoDB export](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataExport_Requesting.html). Those are strong operational properties, but they do not outweigh the extra correctness protocol for Ripple's small, relational state model. It remains a valid fallback if the Aurora cost floor proves disproportionate in the measured billing proof.

### Why not Cloud SQL by default

Google supports GitHub Actions OIDC through Workload Identity Federation without service-account keys, and Cloud Storage supports Object Versioning and retention locks. [Google workload federation for deployment pipelines](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines), [Cloud Storage overview](https://cloud.google.com/storage/docs/introduction), [Cloud Storage Object Retention Lock](https://cloud.google.com/storage/docs/object-lock)

Cloud SQL provides backups, PITR, and export to Cloud Storage, but exports are the portable artifact that survives instance deletion; instance backups have narrower lifecycle semantics. [Cloud SQL backup/export guidance](https://cloud.google.com/sql/docs/postgres/best-practices), [Cloud SQL PITR](https://cloud.google.com/sql/docs/postgres/backup-recovery/configure-pitr). Its smallest shared-core machine types are documented for low-cost test/development and are excluded from the Cloud SQL SLA. [Cloud SQL instance settings](https://cloud.google.com/sql/docs/postgres/instance-settings). A GitHub-hosted runner would also need the Cloud SQL Auth Proxy/connector and reachable public or private networking; the proxy supplies IAM authorization and encryption but does not create network reachability. [Cloud SQL Auth Proxy](https://github.com/GoogleCloudPlatform/cloud-sql-proxy/blob/main/docs/cmd/cloud-sql-proxy.md)

## Hands-on proofs still required

No provider should be selected as “done” until all of these pass in a disposable non-production environment:

1. **Compatibility and cost floor:** create the exact Aurora PostgreSQL version in the intended Region with Serverless v2 minimum 0 ACUs and Data API enabled; observe one week of actual billed compute, storage, I/O, Data API, Secrets Manager, S3, and backup usage.
2. **OIDC boundary:** from the protected GitHub Environment, assume only the runtime role; prove Data API transaction and audit upload succeed while schema change, S3 delete, retention bypass, snapshot deletion, and access outside the configured ARNs fail.
3. **Atomic failure injection:** kill the runner between each operation in plan publication, submission-start, broker acknowledgement, risk update, and reconciliation; prove no partial transaction becomes executable truth.
4. **Uniqueness race:** run two independent workers against the same `order_id`, broker `ref_id`, and plan publication; exactly one commit must succeed.
5. **Lease and fencing race:** contend from two runners, let the first lease expire, let the second acquire, then resume the first; every stale-token write from the first must fail.
6. **Append-only enforcement:** using the actual runtime role, prove published `OrderPlan` and existing `ExecutionEvent` rows cannot be updated or deleted even with malformed application requests.
7. **Object immutability:** upload two versions under one key, verify version IDs and hashes, then prove the runtime role cannot overwrite history destructively, delete a version, shorten retention, or bypass governance mode.
8. **Restore drills:** restore PITR to a fresh cluster and restore a manual snapshot. After the secure logical-export path is designed, restore its dump into a clean PostgreSQL database; compare row counts, constraints, audit URIs, version IDs, and content hashes.
9. **Cold-start timing:** invoke Data API after more than 24 hours idle and confirm all runner timeouts tolerate the documented 30-second-or-longer deep-sleep resume without triggering a duplicate scheduler attempt.

Passing these proofs would justify updating D15 from a semantic decision to an actual vendor selection. Until then, this report is a recommendation, not deployment evidence.

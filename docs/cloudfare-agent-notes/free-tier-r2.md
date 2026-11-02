# R2 Free Tier — Blindspots & Edge Cases

> **Goal: keep R2 at $0/month.** Read this before touching R2 config, buckets, or app code that talks to R2.

## The free allowance (Standard storage only, per month)

| Resource | Free | What counts |
|---|---|---|
| Storage | 10 GB-month | Averaged peak storage per day over the billing period |
| Class A Operations | 1 million | Writes, lists, multipart uploads, bucket creation |
| Class B Operations | 10 million | Reads, HEAD, object downloads |
| Egress | Free, always | Data sent to the internet — no cap |

## Hard rules to stay free

1. **Never enable Infrequent Access storage.** The free tier does NOT apply to it. IA charges per GB stored + a $0.01/GB retrieval fee. Default all buckets to Standard.
2. **Never exceed 10 GB stored.** Billing rounds UP — 10.1 GB = billed for 11 GB-month. Leave headroom; aim to stay under ~9 GB.
3. **Watch Class A ops.** These are the expensive ones ($4.50/million overage). A loop that writes/overwrites objects, or a `ListObjects` call in a hot path, can blow through 1M fast. Cache list results; batch writes.
4. **Egress is free** — don't worry about download volume. But reads (Class B) are not; 10M reads/month is the cap.

## Common blindspots

- **Multipart uploads left incomplete.** Incomplete multipart uploads count toward storage until aborted. Set a lifecycle rule to abort incomplete uploads after a few days.
- **Object versions / overwrites.** Each PUT is a Class A op. Repeatedly overwriting the same key in a loop = many Class A charges. Write once, update rarely.
- **List operations are Class A.** `ListObjectsV2`, `HeadBucket`, listing with a prefix — all Class A. Don't list in request hot paths; cache the result.
- **r2.dev public URL is rate-limited** and not for production. It's fine for dev/testing but can cause failed reads if hit hard. Use a custom domain for real traffic (custom domains also get CDN caching for free).
- **Presigned URLs only work on the S3 API endpoint**, not custom domains. If you need authenticated access on a custom domain, that requires WAF HMAC (check plan requirements).
- **Lifecycle rules themselves don't cost money** but transitioning objects to Infrequent Access via lifecycle rules WILL start incurring IA charges. Only use lifecycle rules to delete or abort — never to transition to IA.
- **Billable unit rounding is aggressive.** Usage is rounded up to the next whole unit. 1 extra operation = billed for 1 million. 1 extra GB-month = billed for 1 GB-month ($0.015). Stay well under limits, not right at the edge.

## Safeguards to set up immediately

- [ ] Set a **budget alert** in the Cloudflare dashboard (account-level, not just R2) at a low threshold (e.g. $1) so you're warned before any charge.
- [ ] Add a **lifecycle rule** on every bucket: abort incomplete multipart uploads after ~1-3 days.
- [ ] Keep all buckets on **Standard storage class**.
- [ ] Monitor usage in the R2 overview dashboard regularly.

## Quick mental model

Storage ≤ 10 GB → free Class A ≤ 1M ops/month → free (writes, lists, uploads — the expensive ones) Class B ≤ 10M ops/month → free (reads, downloads) Egress unlimited → always free Infrequent Access → NEVER free, avoid entirely


## If an AI agent is editing this project's R2 code

- Do not add Infrequent Access storage class to any bucket or object.
- Do not introduce hot-path `ListObjects` calls — cache them.
- Do not write/overwrite objects in loops — batch and minimize Class A ops.
- Do not enable lifecycle transitions to Infrequent Access.
- Default new buckets to Standard storage.
- Flag any code change that could spike storage above 10 GB or Class A ops above 1M/month.

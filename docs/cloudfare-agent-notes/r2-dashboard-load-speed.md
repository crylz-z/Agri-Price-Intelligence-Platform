# Dashboard load speed from R2 at $0/month

Research note, 2026-11-06. It covers how to make `src/dashboard/data.py` load the marts faster while R2 stays on the free tier (`free-tier-r2.md`). Every size and timing below was measured in this session on copies of the live marts. Nothing was written to R2. Claims the primary sources do not state are marked **unverified**.

**Status 2026-11-07:** step 2 (slice marts) is dropped. The dashboard was cut to 3 pages (ADR 12), so the per-page details below describe the old 5-page version.

## Recommendation (ranked)

| # | Change | Expected gain | Effort | R2 cost impact |
|---|---|---|---|---|
| 1 | **Dashboard slice marts**: two small dbt marts with national rows for all months (dishes) or 13 months (staples), region rows for the last 13 months, and province rows for the latest month only | First page: 10.3 MB → **0.37 MB** (28x smaller) | 2 dbt models + tests; change the `data.load` paths | +2 PUTs per build, +0.4 MB stored |
| 2 | **Leaner Parquet**: round the ratio columns to 4 dp, store prices as `DECIMAL(10,2)`, write zstd, and sort retail by `commodity, geo_code, month` | staples 8.99 → 4.0 MB, dishes 1.33 → 0.53 MB, retail 2.96 → 1.57 MB | The intermediate models plus a `compression` option; recompute tests need a tolerance | None |
| 3 | **Fail fast**: put a total deadline on each fetch (`fs.cat_file(path, timeout=…)`), stop retrying the same thing at three nested levels, and use parallel range GETs for files over ~1 MB | A stall ends at a known deadline instead of looping. On the PH link, 8 parallel ranges fetched 1.33 MB in 17 s while one stream stalled for 150 s | Small edits to `storage.py` and `data.py` | A few extra Class B per load, about 0.03% of the quota |
| 4 | **Streamlit**: `refresh_mode="background"` on `load`, and categorical strings or `st.cache_resource` | No visitor waits when the TTL expires. Staples memory 134 → 22 MB and per-call copy 104 → 6 ms | 1–3 lines in `data.py`; categoricals need a test pass | None |
| 5 | **Custom domain + Cloudflare Cache** in front of a public bucket | Mainly helps the **US** Streamlit server reach the **APAC** bucket. Whether cache hits are free of Class B is unverified | Needs a domain added as a Cloudflare zone, a Cache Rule, and a rate-limit rule | Free plan features. A domain registration costs money (outside R2) |

Not recommended:
- **`persist="disk"`**: it ignores `ttl`, so stale data would stay until the app reboots.
- **r2.dev**: it has no cache and is rate-limited.
- **DuckDB over s3fs in the app**: it made 57 range reads.
- **pyarrow `filters` over the current files**: they are sorted by month, so a commodity filter still reads 99% of retail.

**One premise to correct:** the marts are **Snappy**, not zstd. All four files report `created_by DuckDB v1.4.4` and `SNAPPY` on every column chunk. `dbt/` sets no codec, and DuckDB's default is Snappy ([DuckDB Parquet docs](https://duckdb.org/docs/2.0/data/parquet/overview.html)).

**Where the time goes, measured from the PH connection on 2026-11-06 at about 22:30 PHT:**
- **DNS**: the first DNS lookup of the R2 endpoint took **7.7 s**. Repeat lookups took 0.01–0.02 s. The 5 MB Cloudflare speed test also had a 7.9 s TTFB, so this is local DNS, not R2.
- **Edge and bucket**: R2 answered from the `MNL` colo (`CF-RAY …-MNL`), and `GetBucketLocation` returned `APAC`.
- **Single stream**: with a presigned URL and plain `curl`, `dish_costs_monthly` took 0.26 s to first byte, then crawled at **4 KB/s** and stopped at 606 KB after 150 s. Python and botocore are not the cause.
- **Cloudflare speed test**: 462 KB/s at the same time.
- **Parallel range GETs** with `fs.cat_ranges`:

| Mart | Size | Ranges | Time | Throughput |
|---|---|---|---|---|
| dishes | 1.33 MB | 8 | 17.1 s | 76 KB/s |
| retail | 2.96 MB | 16 | 23.3 s | 124 KB/s |
| staples | 8.99 MB | 16 | 212 s | 41 KB/s |

A single `cat_file` of staples did not finish in 300 s. Throughput per connection to R2 from this network is the bottleneck, so fewer bytes (#1, #2) is the lever that works everywhere.

**Production is a different path.** Community Cloud "hosts all apps in the United States" ([Streamlit status page](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)). Its outbound IPs (35.230.x, 34.127.x and others) look like GCP, but the exact region is **unverified**. The Streamlit server fetches from R2; the visitor's browser never talks to R2. So in production the R2 leg is US ↔ APAC bucket, and the visitor's leg is PH ↔ US over the Streamlit websocket. The PH-to-R2 numbers above describe local development only.

## 1. Smaller dashboard marts

What the pages use, from `src/dashboard/views.py`:
- **This month**: the place picker lists only national and regions (`data.regions`). Sparklines take 13 months of `history(..., geo_code, 13)` for staples and dishes.
- **Map**: `area_values` and `place_basket` use the latest month at any level.
- **Dish page**: `history(dishes, "dish", dish, PHILIPPINES)` uses the full national dish series.
- **Look up a price**: needs any commodity × place series, so it keeps the full retail mart.

Rows by level in `staple_prices_monthly`: 2,968 national, 50,902 region, 229,194 province, across 106 months (2018-01 to 2026-10). Province rows are 81% of the file.

Sizes of the real data sliced with DuckDB 1.4.4, zstd:

| Variant | Rows | Size |
|---|---|---|
| staples, current file | 283,064 | 8.99 MB |
| staples slice (nat+reg last 13 mo, province latest) | 8,872 | 0.289 MB |
| staples slice + ratios rounded to 4 dp | 8,872 | **0.181 MB** |
| dishes, current file | 100,912 | 1.33 MB |
| dishes slice (national all months, region last 13, province latest) | 3,520 | **0.078 MB** |
| seasonality | 336 | 0.004 MB |

The first page would then load about 0.26–0.37 MB instead of 10.3 MB.

This keeps ADR 9, because the numbers are still computed and tested in dbt. dbt-duckdb's `external` materialization writes each model to its own `location` ([dbt-duckdb README](https://github.com/duckdb/dbt-duckdb/blob/master/README.md)), so the cost is one PUT (Class A) per slice per build and about 0.4 MB of storage.

The current marts stay in place for the lookup page and for `src.etl.query`.

**Dropping columns** helps less than slicing:
- `change_month`, `change_year` and `vs_national` are 6.1 MB of the 8.99 MB staples file. They are full-precision doubles that compress poorly.
- Dropping them leaves 2.40 MB, but the dashboard reads all three, so this would move logic out of dbt (against ADR 9). Rounding (section 5) gets most of the gain without that.

## 2. Column and row-group pruning on read

- **Filters and columns**: `pyarrow.parquet.read_table(columns=…, filters=…)` reads only the chosen columns and drops rows that do not match ([pyarrow docs](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.read_table.html)). Whole row groups are skipped only when the min/max statistics rule them out.
- **Coalescing**: `pre_buffer=True` makes pyarrow "coalesce and issue file reads in parallel … on high-latency filesystems (e.g. S3)". The same docs say: "If using a filesystem layer that itself performs readahead (e.g. fsspec's S3FS), disable readahead for best results."
- **s3fs readahead**: s3fs defaults to `default_cache_type="readahead"` with `default_block_size = 50 MiB` (`s3fs/core.py`, s3fs 2026.2.0). So a `pq.read_table(fs.open(path))` on these files fetches the whole object on the first read anyway. To prune, open with `cache_type="none"` or pass byte ranges.
- **Gap merging**: Arrow merges ranges whose gaps are at most `hole_size_limit` = 8 KiB, up to `range_size_limit` = 32 MiB. These are the defaults of `pyarrow.CacheOptions()` in pyarrow 23.0.1, read locally.

IO requests pyarrow made, counted with a logging file object on local copies:

| File / query | IO requests (pre_buffer on / off) | Bytes read |
|---|---|---|
| retail as-is (sorted by month), one commodity | 2 / 49 | 2.92 of 2.96 MB: no pruning |
| retail sorted by commodity, 122,880-row groups, one commodity | 2 / 9 | 0.275 of 1.57 MB |
| same, 20,000-row groups (36 groups) | 2 / 17 | 0.152 of 1.52 MB |
| staples as-is, provinces in latest month | 2 / 17 | 1.42 of 8.99 MB |

With `pre_buffer`, a filtered read costs about 1 HEAD (s3fs `info` for the size) + 2–3 range GETs, all Class B ([R2 pricing](https://developers.cloudflare.com/r2/pricing/): `GetObject` and `HeadObject` are Class B). That is negligible against 10M a month.

Verdict: worth it only for the lookup page, after retail is sorted by commodity. It would then fetch about 0.15–0.3 MB per selected commodity, plus a small read of the `commodity` and geo columns for the pickers. For the first page, the slice marts (#1) are simpler and smaller. The 57-read DuckDB result is consistent with unbuffered reads (49 here with `pre_buffer` off).

## 3. Public bucket: r2.dev versus a custom domain with cache

**r2.dev**:
- It is "rate-limited and should only be used for development purposes" ([public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)).
- Over the limit ("hundreds of requests/second") it returns 429, and throughput may be throttled ([R2 limits](https://developers.cloudflare.com/r2/reference/limits/)).
- It "does not support caching, WAF, or bot management" ([Cache + R2](https://developers.cloudflare.com/cache/interaction-cloudflare-products/r2/)).
- Not recommended.

**Custom domain**:
- It enables Cloudflare Cache. The domain "must have been added as a zone in the same account as the R2 bucket" ([public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)).
- With cache on, "read requests can bypass the R2 Gateway and be served directly from Cloudflare's edge cache", but "cached data may not reflect the latest version immediately" ([How R2 works](https://developers.cloudflare.com/r2/how-r2-works/)).
- **Parquet needs a Cache Rule.** `.parquet` is not in Cloudflare's default cached extensions ([default cache behavior](https://developers.cloudflare.com/cache/concepts/default-cache-behavior/)). The Free plan includes 10 Cache Rules ([Cache Rules](https://developers.cloudflare.com/cache/how-to/cache-rules/)).
- **Default edge TTL** for a 200 with no `Cache-Control` is 120 min. The Free plan caches files up to 512 MB.
- **Tiered cache**: Smart Tiered Cache is on every plan ([Tiered Cache](https://developers.cloudflare.com/cache/how-to/tiered-cache/)), and Cloudflare suggests it for R2 so that "a single upper-tier data center next to your R2 bucket" serves misses ([public buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)).

**Class B on cache hits: unverified.** The R2 pricing page does not say whether a cache hit counts as an R2 operation. Docs only say hits bypass the R2 Gateway. Community forum threads say hits are not billed, but they are not a primary source. Cache Reserve (a separate paid product) does bill hits as Class B ([Cache Reserve](https://developers.cloudflare.com/cache/advanced-configuration/cache-reserve/)). At this app's traffic, about 16 GETs a day at a 6 h TTL, Class B is not at risk either way.

**Speed**: in production the Streamlit server is in the US and the bucket's location hint is APAC ([data location](https://developers.cloudflare.com/r2/reference/data-location/): `apac` is one hint; hints are fixed at creation). A US edge cache would put the marts next to the server. For local development from the PH, the R2 S3 endpoint is already answered at the MNL colo, so the slow body transfer would not obviously improve. **Unverified**: no measurement of a cached custom-domain fetch was possible without changing the bucket.

**Security trade-off**:
- The marts are public PSA data, so confidentiality is not the issue. A public URL lets anyone trigger GETs.
- Cache misses and 404s cost Class B, a quota owned by this project.
- Mitigations: the Free plan gets one rate-limiting rule, counted by IP over 10 s ([rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/)), and a Cache Rule can cache 404s.
- Presigned URLs work only on the S3 endpoint, not on custom domains (`free-tier-r2.md`).
- Keep `raw/` private: serve only `mart/` paths, using a separate bucket or a WAF rule on the path.

**Cost**: the Cloudflare Free plan features are $0, and egress is free ([R2 pricing](https://developers.cloudflare.com/r2/pricing/)). A domain must be registered or already owned, which is a non-R2 cost.

## 4. Streamlit options

- **`persist="disk"`**: "`ttl` will be ignored if `persist="disk"` or `persist=True`" ([st.cache_data](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)). Streamlit also logs a warning, from `LocalDiskCacheStorageManager.check_context` in streamlit 1.66.1. A new PSA release would then not appear until a reboot. Whether Community Cloud keeps local disk across sleep or reboot is **unverified**: the docs say only that a reboot will "clear its memory" ([manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)). Not recommended.
- **`refresh_mode="background"`** (in 1.66.1, the installed version): when `ttl` expires it will "return the expired value immediately and update it in the background", by default for one extra `ttl`. It "requires a `ttl` and can't be used with `persist`" ([st.cache_data](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)). Only the first visitor after a cold start would wait. Recommended: one keyword on `load`.
- **Copies**: `st.cache_data` "creates a new copy of the data at each function call" by pickling. `st.cache_resource` stores the object itself, with no copy ([caching concepts](https://docs.streamlit.io/develop/concepts/architecture/caching)). Measured locally, in ms per rerun per mart:

| Mart | Unpickle (copy) | Parse + `to_pandas` | Memory as object strings |
|---|---|---|---|
| staples | 104 | 870 | 134 MB |
| retail | 189 | 201 | 247 MB |
| dishes | 28 | 43 | 39 MB |

  With `to_pandas(strings_to_categorical=True)`, staples drops to 22 MB, 6 ms unpickle and 36 ms parse. Code that compares or merges on those columns needs re-testing. `cache_resource` removes the copy but shares one mutable object across sessions.
- **Resource limits**: Community Cloud gives 0.078–2 cores and 690 MB–2.7 GB memory, and apps sleep after 12 h without traffic ([manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)). About 420 MB of pandas frames plus their pickles is a real share of a 690 MB floor. #1 and categoricals both relieve it.
- **Render before data**: fragments run inline in order unless `parallel=True`. On a full rerun, a parallel fragment "is dispatched to a thread pool" and runs alongside the main script ([fragments](https://docs.streamlit.io/develop/concepts/architecture/fragments)). Limits: parallel fragments cannot write to containers created outside them, and caching a fragment function is unsupported. One use: render the page header from the small marts, and load the retail table on the lookup page in a parallel fragment behind `show_spinner`.
- **Warming caches**: no Streamlit doc describes pre-warming `st.cache_data` at startup or keeping a Community Cloud app awake. **Unverified** whether an external ping of the app URL counts as traffic that prevents sleep.

## 5. Compression and Parquet settings

DuckDB rewrites of the real data (sizes in MB):

| Mart | Snappy (now) | zstd default | zstd level 19 | Best content change + zstd |
|---|---|---|---|---|
| staples | 8.99 | 7.52 | 7.24 | 4.24 (round ratios to 4 dp); 4.03 (+ `DECIMAL(10,2)` prices) |
| dishes | 1.33 | 1.10 | 1.06 | 0.61 (round ratios); 0.53 (+ costs to 2 dp) |
| retail | 2.96 | 2.09 | 1.87 | 1.84 (`DECIMAL(10,2)` price); 1.57 (+ sort by commodity, geo_code, month) |

Notes:
- **Codec and level**: zstd alone saves 16–30%, and level 19 adds only 3–10%. The big win is content: full-precision ratio doubles barely compress. 4 dp keeps the dashboard's 0.1% display exact. All retail and staple prices are already exactly 2 dp (0 rows differ), so `DECIMAL(10,2)` is lossless.
- **Setting it in dbt**: dbt-duckdb passes `options` to DuckDB's `COPY` ([README](https://github.com/duckdb/dbt-duckdb/blob/master/README.md)). DuckDB's `COPY … (FORMAT parquet, COMPRESSION zstd)` was used for every test above. Exact key spelling in the dbt config is **unverified** until a `dbt compile`.
- **Dictionary encoding** is already on for strings and low-cardinality doubles (`PLAIN_DICTIONARY` in the metadata). Nothing to gain there.
- **Row group size**: it matters only for pruning (section 2). At 20,000 rows, retail sorted by commodity reads 0.15 MB per commodity. 5,000-row groups made the file bigger (1.76 MB) and the read no smaller.
- **Recompute tests**: rounding interacts with `assert_*_recompute.sql`. Round in the mart, or compare with a tolerance.

## 6. Timeouts and retries

- **`read_timeout` is per socket read, not per request.** aiobotocore 3.1.3 maps it to `aiohttp.ClientTimeout(sock_connect=conn_timeout, sock_read=read_timeout)` and sets no `total` (`aiobotocore/httpsession.py`). aiohttp defines `sock_read` as "maximal number of seconds for reading a portion of data from a peer" and `total` as the whole request, default `None` here ([aiohttp ClientTimeout](https://docs.aiohttp.org/en/stable/client_reference.html)). A 4 KB/s trickle never trips a 20 s `sock_read`, so a download can run for minutes. That is what was measured.
- **`max_attempts: 3` means 4 attempts.** In botocore, `max_attempts` counts retries after the first request; `total_max_attempts` counts all attempts ([botocore Config](https://docs.aws.amazon.com/botocore/latest/reference/config.html)).
- **Retries are nested three deep.** In s3fs 2026.2.0, `_cat_file` wraps `_call_and_read` in `_error_wrapper(retries=self.retries)`. That calls `_call_s3`, which wraps the botocore call in a second `_error_wrapper(retries=self.retries)`, and `S3FileSystem.retries = 5` (`s3fs/core.py`, [source](https://github.com/fsspec/s3fs/blob/main/s3fs/core.py)). Connection errors can therefore reach 5 × 5 × 4 attempts. A body-read failure restarts the whole GET up to 5 times. Each restart is a new Class B op and starts again from byte 0.
- **A total deadline already exists.** fsspec's sync wrapper accepts `timeout=`: `sync(loop, func, *args, timeout=None, **kwargs)` wraps the coroutine in `asyncio.wait_for` and raises `FSTimeoutError` ([fsspec asyn.py](https://github.com/fsspec/filesystem_spec/blob/master/fsspec/asyn.py)). `fs.cat_file(path, timeout=90)` was verified this session: it raised `FSTimeoutError` at 90.0 s on a stalled dishes download, and `cat_ranges(..., timeout=240)` worked the same way.

Suggested settings, for local development and the server:
- `"retries": {"total_max_attempts": 2, "mode": "standard"}`, `read_timeout` about 10, and `tcp_keepalive=True`.
- `fs.retries = 1` on the instance, so s3fs does not multiply the retries.
- One application-level retry around `cat_file(path, timeout=…)`, with the deadline sized to the expected file. After #1 and #2 that is under 1 MB, so 30 s is generous even at 40 KB/s.
- For files over ~1 MB on slow links, `fs.cat_ranges([path]*n, starts, ends, timeout=…)` after one `fs.info` (HEAD). This cost 9–17 Class B per mart here and was the only way the 9 MB file arrived at all.

## Other findings

- **Class B budget**: a 6 h TTL gives about 4 loads a day × 4 marts on one server, about 500 GETs a month. Even 17 ranges per mart is about 8,000 a month, 0.08% of 10M. None of the options above threaten the $0 limit. Only #1 adds Class A: 2 PUTs per build.
- **Lookup page loads**: it uses only `retail` and `seasons`, so after #1 it is the one page still pulling about 1.6–3 MB. Combine #2 (sorted retail) with either a whole-file fetch or a column- and row-group-pruned read (section 2).

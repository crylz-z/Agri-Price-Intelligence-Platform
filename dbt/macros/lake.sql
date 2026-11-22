{% macro lake_root() %}
  {#- Override with --vars '{lake_root: <dir>}' to build against a local copy. -#}
  {{ return(var('lake_root', 's3://' ~ env_var('S3_BUCKET_NAME', ''))) }}
{% endmacro %}


{% macro psa_snapshot_files(kind='retail', keep=2) %}
  {#- The newest `keep` snapshots per table, newest first. One glob lists raw/.
      kind 'farmgate', 'wholesale' or 'cpi' means the tables in
      seeds/psa_<kind>_tables.csv;
      'retail' is every other table, so a table PSA adds still reaches the retail
      tests. The calling model needs
      `-- depends_on: {{ ref('psa_farmgate_tables') }}, {{ ref('psa_wholesale_tables') }},
      {{ ref('psa_cpi_tables') }}`. -#}
  {% if not execute %}{{ return([]) }}{% endif %}
  {% set chosen = {
    'farmgate': ref('psa_farmgate_tables'),
    'wholesale': ref('psa_wholesale_tables'),
    'cpi': ref('psa_cpi_tables'),
  } %}
  {% set sql %}
    select file from (
      select file, regexp_extract(file, 'table=(\w+)', 1) as table_id,
        row_number() over (partition by table_id order by file desc) as snapshot_rank
      from glob('{{ lake_root() }}/raw/table=*/updated=*.csv')
    )
    where snapshot_rank <= {{ keep }}
    {% if kind == 'retail' %}
      {% for seed in chosen.values() %}
      and table_id not in (select table_id from {{ seed }})
      {% endfor %}
    {% else %}
      and table_id in (select table_id from {{ chosen[kind] }})
    {% endif %}
    order by file
  {% endset %}
  {% set files = run_query(sql).columns[0].values() %}
  {% if files | length == 0 %}
    {{ exceptions.raise_compiler_error("No PSA " ~ kind ~ " snapshots under " ~ lake_root() ~ "/raw") }}
  {% endif %}
  {{ return(files) }}
{% endmacro %}

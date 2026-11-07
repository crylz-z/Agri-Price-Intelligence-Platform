{% macro lake_root() %}
  {#- Override with --vars '{lake_root: <dir>}' to build against a local copy. -#}
  {{ return(var('lake_root', 's3://' ~ env_var('S3_BUCKET_NAME', ''))) }}
{% endmacro %}


{% macro psa_snapshot_files(farmgate=false, keep=2) %}
  {#- The newest `keep` snapshots per table, newest first. One glob lists raw/.
      Farmgate tables are the ones in seeds/psa_farmgate_tables.csv; every other
      table is retail, so a table PSA adds still reaches the retail tests.
      The calling model needs `-- depends_on: {{ ref('psa_farmgate_tables') }}`. -#}
  {% if not execute %}{{ return([]) }}{% endif %}
  {% set sql %}
    select file from (
      select file, regexp_extract(file, 'table=(\w+)', 1) as table_id,
        row_number() over (partition by table_id order by file desc) as snapshot_rank
      from glob('{{ lake_root() }}/raw/table=*/updated=*.csv')
    )
    where snapshot_rank <= {{ keep }}
      and table_id {{ '' if farmgate else 'not' }} in (
        select table_id from {{ ref('psa_farmgate_tables') }}
      )
    order by file
  {% endset %}
  {% set files = run_query(sql).columns[0].values() %}
  {% if files | length == 0 %}
    {{ exceptions.raise_compiler_error("No PSA snapshots under " ~ lake_root() ~ "/raw") }}
  {% endif %}
  {{ return(files) }}
{% endmacro %}

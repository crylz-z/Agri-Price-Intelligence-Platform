{% macro lake_root() %}
  {#- Override with --vars '{lake_root: <dir>}' to build against a local copy. -#}
  {{ return(var('lake_root', 's3://' ~ env_var('S3_BUCKET_NAME', ''))) }}
{% endmacro %}


{% macro psa_snapshot_files(keep=2) %}
  {#- The newest `keep` snapshots per table, newest first. One glob lists raw/. -#}
  {% if not execute %}{{ return([]) }}{% endif %}
  {% set sql %}
    select file from (
      select file, row_number() over (
        partition by regexp_extract(file, 'table=(\w+)', 1) order by file desc
      ) as snapshot_rank
      from glob('{{ lake_root() }}/raw/table=*/updated=*.csv')
    )
    where snapshot_rank <= {{ keep }}
    order by file
  {% endset %}
  {% set files = run_query(sql).columns[0].values() %}
  {% if files | length == 0 %}
    {{ exceptions.raise_compiler_error("No PSA snapshots under " ~ lake_root() ~ "/raw") }}
  {% endif %}
  {{ return(files) }}
{% endmacro %}

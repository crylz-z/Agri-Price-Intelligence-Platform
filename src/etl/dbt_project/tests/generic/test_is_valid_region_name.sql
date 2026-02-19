{% test is_valid_region_name(model, column_name) %}

    select *
    from {{ model }}
    where
    -- Fails if region_name consists ONLY of digits and dots (e.g. "1000000", "40000000.0")
    regexp_matches(cast({{ column_name }} as string), '^[0-9.]+$')

{% endtest %}

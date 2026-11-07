{{ config(severity='warn') }}

-- A farmgate price above retail can be real (a month of glut at retail, a shortage
-- at the farm, or rice stored for months), so this only warns.
select month, geo_code, staple, farmgate_equivalent, retail_price, farmer_share
from {{ ref('int_farmer_share') }}
where farmer_share <= 0 or farmer_share > 1

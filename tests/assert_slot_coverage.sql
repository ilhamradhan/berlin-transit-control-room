select *
from {{ ref('mart_reliability') }}
where covered_slot_count > slot_count
   or covered_slot_count < 0
   or slot_count < 1
   or observation_count < entity_count

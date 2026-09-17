select *
from {{ ref('int_reliability_observations') }}
where entity_id is null
   or trip_id is null
   or route_id is null
   or stop_id is null
   or slot_utc is null
   or scheduled_event_utc is null
   or predicted_event_utc is null

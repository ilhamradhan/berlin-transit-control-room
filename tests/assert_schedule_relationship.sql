select *
from {{ ref('int_reliability_observations') }}
where schedule_relationship <> 'SCHEDULED'
   or delay_seconds <> epoch(predicted_event_utc - scheduled_event_utc)

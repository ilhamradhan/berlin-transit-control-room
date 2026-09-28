select *
from {{ ref('int_reliability_observations') }}
where (data_origin = 'synthetic' and (
          schedule_relationship <> 'SCHEDULED'
          or delay_seconds <> epoch(predicted_event_utc - scheduled_event_utc)
      ))
   or (data_origin = 'real' and (
          schedule_relationship not in ('SCHEDULED', 'CANCELED')
          or delay_seconds is null
      ))

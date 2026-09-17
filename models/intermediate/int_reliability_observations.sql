select
    *,
    delay_seconds <= 300 as is_on_time,
    delay_seconds > 900 as is_severe_delay
from {{ ref('stg_observations') }}

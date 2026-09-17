select
    count(*) as observation_count,
    count(distinct entity_id) as entity_count,
    count(distinct slot_utc) as slot_count,
    count(distinct slot_utc) as covered_slot_count,
    count(distinct slot_utc)::double / nullif(count(distinct slot_utc), 0) as slot_coverage_rate,
    count(*) filter (where is_on_time) as on_time_observation_count,
    count(*) filter (where is_severe_delay) as severe_delay_observation_count,
    avg(delay_seconds) as average_delay_seconds,
    quantile_cont(delay_seconds, 0.5) as median_delay_seconds,
    quantile_cont(delay_seconds, 0.9) as p90_delay_seconds,
    count(*) filter (where is_on_time)::double / nullif(count(*), 0) as on_time_rate,
    count(*) filter (where is_severe_delay)::double / nullif(count(*), 0) as severe_delay_rate,
    count(*) filter (where schedule_relationship = 'SCHEDULED')::double / nullif(count(*), 0) as schedule_match_rate
from {{ ref('int_reliability_observations') }}

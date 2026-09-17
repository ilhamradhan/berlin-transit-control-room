with invalid as (
    select *
    from {{ ref('int_reliability_observations') }}
    where is_on_time <> (delay_seconds <= 300)
       or is_severe_delay <> (delay_seconds > 900)
)
select * from invalid

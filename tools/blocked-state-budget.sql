WITH operation AS (
  SELECT s.id, s.ts, s.dur, tt.utid
  FROM slice s
  JOIN thread_track tt ON tt.id = s.track_id
  WHERE s.name = 'CG/blocked/snapshot' AND s.dur >= 0
), clipped AS (
  SELECT o.id, st.state,
    MIN(st.ts + st.dur, o.ts + o.dur)
      - MAX(st.ts, o.ts) AS overlap_ns
  FROM operation o
  JOIN thread_state st ON st.utid = o.utid
  WHERE st.dur >= 0
    AND st.ts < o.ts + o.dur
    AND st.ts + st.dur > o.ts
)
SELECT id, state, SUM(overlap_ns) AS duration_ns
FROM clipped
GROUP BY id, state
ORDER BY id, state;

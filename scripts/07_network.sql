-- T16 Stage B v3: topology patch — pre-create source/target so pgr_createTopology
-- doesn't trip on its own column detection
BEGIN;
ALTER TABLE argos.road_net ADD COLUMN IF NOT EXISTS source integer;
ALTER TABLE argos.road_net ADD COLUMN IF NOT EXISTS target integer;
SELECT pgr_createTopology('argos.road_net', 0.00001, 'geom', 'id', clean := true);
COMMIT;

-- connectivity report
SELECT component, count(*) AS vertices
FROM pgr_connectedComponents(
  'SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_net')
GROUP BY component ORDER BY 2 DESC LIMIT 6;

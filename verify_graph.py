from src.entity_resolution.service import EntityGraphService
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.authorization.policy_engine import PolicyEngine
from src.auth.models import TokenPayload, UserRole
from collections import Counter
import time

gi = KuzuEntityGraphIntegrator()
gi.setup()
pe = PolicyEngine()

actor = TokenPayload(
    sub='USER-OFFICER-001',
    username='officer1',
    role=UserRole.INVESTIGATION_OFFICER,
    authorized_case_ids=['CASE-2026-C1EA'],
    exp=int(time.time()) + 3600,
    jti='test-jti'
)

svc = EntityGraphService(
    graph_integrator=gi,
    policy_engine=pe,
)

g = svc.get_case_graph(actor, 'CASE-2026-C1EA', demo=False)
print('is_empty:', g.get('is_empty'))
print('total_nodes:', len(g.get('nodes', [])))
print('total_edges:', len(g.get('edges', [])))

layers = Counter(n['layer'] for n in g.get('nodes', []))
print('Nodes per layer:', sorted(layers.items()))

for n in g.get('nodes', []):
    print(f"  [Layer {n['layer']}] {n['label']} ({n['entity_type']})")

print(f"\nSample edges ({len(g.get('edges', []))}):")
for e in g.get('edges', [])[:10]:
    print(f"  {e['source']} --[{e['relationship_type']}]--> {e['target']} (CCC: {e['ccc_score']}, Ring: {e['ccc_ring']})")

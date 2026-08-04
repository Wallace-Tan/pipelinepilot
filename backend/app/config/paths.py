from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = PROJECT_ROOT / "data/fixtures/schema_drift"
POLICY_PATH = PROJECT_ROOT / "data/policies/demo_policy.json"
RECOMMENDATION_PATH = FIXTURE_ROOT / "expected_recommendation.json"
RUNBOOKS_ROOT = PROJECT_ROOT / "data/runbooks"

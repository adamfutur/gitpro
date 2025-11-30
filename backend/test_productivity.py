"""
Test script to verify productivity score calculation
"""
from services.kpi_calculator import _calculate_productivity_kpis

# Test with your data: 5 commits, 0 PRs, 1 contributor
mock_commits = [
    {'commit': {'author': {'name': 'User1'}}},
    {'commit': {'author': {'name': 'User1'}}},
    {'commit': {'author': {'name': 'User1'}}},
    {'commit': {'author': {'name': 'User1'}}},
    {'commit': {'author': {'name': 'User1'}}},
]

mock_prs = []

result = _calculate_productivity_kpis(mock_commits, mock_prs)

print("=" * 50)
print("PRODUCTIVITY KPI TEST")
print("=" * 50)
print(f"Commits: {len(mock_commits)}")
print(f"PRs: {len(mock_prs)}")
print(f"Contributors: 1")
print("\nResult:")
for key, value in result.items():
    print(f"  {key}: {value}")
print("=" * 50)

# Expected: productivity_score should be ~41.0
expected_score = 41.0
actual_score = result.get('productivity_score', 0)

if abs(actual_score - expected_score) < 1:
    print("✅ TEST PASSED! Productivity score is correct.")
else:
    print(f"❌ TEST FAILED! Expected ~{expected_score}, got {actual_score}")

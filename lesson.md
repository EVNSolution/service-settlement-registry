Source: https://lessons.md

# service-settlement-registry Lessons.md

Registry proof should stay boundary-focused. This repo owns settlement config, policy, and pricing-table truth. It does not own `SettlementRun` or `SettlementItem`, and a successful rollout should not be described as "settlement is done" unless payroll and ops were proven separately.

The honest production smoke for this repo was:

- `/api/settlement-registry/health/` -> `200`
- `/api/settlement-registry/settlement-config/metadata/` -> `401` without token

That was enough to prove the gateway route, app startup, and auth layer without mutating production policy data.

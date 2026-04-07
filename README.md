# service-settlement-registry

이 repo는 정산 기준표와 정책 `registry` 정본 runtime이다.

현재 역할:
- `SettlementPolicy`, `SettlementPolicyVersion`, `SettlementPolicyAssignment` registry CRUD
- 회사/플릿 scope 기준 assignment 관리
- admin-only management API와 `health` endpoint
- deterministic bootstrap seed command

이 repo는 절대 소유하지 않음:
- `SettlementRun`
- `SettlementItem`
- payout/result truth
- run/item CRUD
- delivery source input truth

현재 API:
- internal path: `/health/`
- internal path: `/policies/`
- internal path: `/policy-versions/`
- internal path: `/policy-assignments/`
- gateway prefix: `/api/settlement-registry/`

아직 포함하지 않음:
- payroll direct lookup 연동
- ops-view direct fan-out 연동
- company-only precedence
- driver override
- simulation / dry-run

현재 정본:
- `../../docs/mappings/`
- `../../docs/decisions/specs/2026-03-24-settlement-registry-phase-1-activation-design.md`

이력 / 컨텍스트:
- `../../docs/archive/historical/rollout/2026-03-20-settlement-phase-1-decomposition-implementation-plan.md`
- `../../docs/archive/historical/rollout/2026-03-24-settlement-registry-phase-1-activation-implementation-plan.md`

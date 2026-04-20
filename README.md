# service-settlement-registry

## Purpose / Boundary

이 repo는 정산 기준표와 정책 `registry` 정본 runtime 이다.

현재 역할:
- `SettlementPolicy`, `SettlementPolicyVersion`, `SettlementPolicyAssignment` registry CRUD
- 회사/플릿 scope 기준 assignment 관리
- admin-only management API와 `health` endpoint
- deterministic bootstrap seed command

포함하지 않음:
- `SettlementRun`
- `SettlementItem`
- payout/result truth
- run/item CRUD
- delivery source input truth
- 플랫폼 전체 compose와 gateway 설정

## Runtime Contract / Local Role

- compose service는 `settlement-registry-api` 다.
- gateway prefix는 `/api/settlement-registry/` 다.
- current API:
  - `/health/`
  - `/policies/`
  - `/policy-versions/`
  - `/policy-assignments/`
  - `/settlement-config/metadata/`
  - `/settlement-config/`

## Local Run / Verification

- local run: `. .venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- local test: `. .venv/bin/activate && python manage.py test -v 2`

## Image Build / Deploy Contract

- prod contract is build, test, and immutable image publish only
- production runtime rollout ownership belongs to `runtime-prod-release`
- build and publish auth uses `ECR_BUILD_AWS_ROLE_ARN` plus shared `AWS_REGION`


- GitHub Actions workflow 이름은 `Build service-settlement-registry image` 다.
- workflow는 immutable `service-settlement-registry:<sha>` 이미지를 ECR로 publish 한다.
- runtime rollout은 `../runtime-prod-release/` 가 소유한다.
- production runtime shape와 canonical inventory는 `../runtime-prod-platform/` 이 소유한다.

## Environment Files And Safety Notes

- registry proof는 boundary-focused 여야 한다. run/item 영역까지 옮겼다고 과장하지 않는다.
- honest production proof는 mutation 없이 `health 200 + protected 401` 조합으로 본다.

## Key Tests Or Verification Commands

- full Django tests: `. .venv/bin/activate && python manage.py test -v 2`
- honest smoke는 `/api/settlement-registry/health/` 와 `/api/settlement-registry/settlement-config/metadata/` 조합이다.

## Root Docs / Runbooks

- `../../docs/boundaries/`
- `../../docs/mappings/`
- `../../docs/runbooks/ev-dashboard-ui-smoke-and-decommission.md`
- `../../docs/decisions/specs/2026-03-24-settlement-registry-phase-1-activation-design.md`
- `../../docs/archive/historical/rollout/2026-03-20-settlement-phase-1-decomposition-implementation-plan.md`
- `../../docs/archive/historical/rollout/2026-03-24-settlement-registry-phase-1-activation-implementation-plan.md`

## Root Development Whitelist

- 이 repo는 `clever-msa-platform` root `development/` whitelist에 포함된다.
- root visible set은 `front-web-console`, `edge-api-gateway`, `runtime-prod-release`, `runtime-prod-platform`, active `service-*` repo만 유지한다.
- local stack support repo, legacy infra repo, bridge lane repo는 root `development/` whitelist 바깥에서 관리한다.
- 이 README와 repo-local AGENTS는 운영 안내 문서이며 정본이 아니다. 경계, 계약, 런타임 truth는 root `docs/`를 따른다.

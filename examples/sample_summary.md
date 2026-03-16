# AgentDiff Review Summary

## Summary
- **Files:** 6
- **Groups:** 4
- **Additions:** 51
- **Deletions:** 14
- **High risk files:** 3
- **Medium risk files:** 3
- **Low risk files:** 0

## Risk Hotspots
- `src/api/user_service.py` - high (9/10): Touches authentication/authorization code; Function/method signatures changed; Contains executable behavior changes
- `src/security/auth_utils.py` - high (9/10): Touches authentication/authorization code; Function/method signatures changed; Contains executable behavior changes
- `src/security/token_validator.py` - high (9/10): Touches authentication/authorization code; Function/method signatures changed; Contains executable behavior changes
- `migrations/20260312_add_user_role.sql` - medium (5/10): Modifies schema or migration surface
- `config/app.yaml` - medium (4/10): Changes runtime/build configuration
- `tests/test_user_service.py` - medium (4/10): Function/method signatures changed; Contains executable behavior changes; Primarily non-production surface

## Suggested Review Order
1. `src/security/auth_utils.py` (high) - Planned step: Harden token and permission checks
2. `src/security/token_validator.py` (high) - Planned step: Harden token and permission checks
3. `src/api/user_service.py` (high) - Planned step: Harden token and permission checks
4. `migrations/20260312_add_user_role.sql` (medium) - Planned step: Enable role support
5. `tests/test_user_service.py` (medium) - Planned step: Enable role support
6. `config/app.yaml` (medium) - Planned step: Tune runtime config

## Plan Drift
- Planned but unchanged: 0
- Changed but unplanned: 0

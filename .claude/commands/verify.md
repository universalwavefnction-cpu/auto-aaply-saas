# Verify All Checks Pass

Run every check in order. Stop and fix if any step fails before moving on:

1. **Backend lint**: `cd ~/autoapply-web && ruff check backend/`
2. **Backend format**: `cd ~/autoapply-web && ruff format --check backend/`
3. **Backend tests**: `cd ~/autoapply-web && pytest tests/ -x -q`
4. **Frontend typecheck**: `cd ~/autoapply-web/frontend && bun run typecheck`
5. **Frontend lint**: `cd ~/autoapply-web/frontend && bun run lint`
6. **Frontend format**: `cd ~/autoapply-web/frontend && bun run format:check`
7. **Frontend tests**: `cd ~/autoapply-web/frontend && bun run test`

If all pass, report "All checks pass." If any fail, fix the issues and re-run that step.

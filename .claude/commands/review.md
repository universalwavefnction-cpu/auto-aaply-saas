# Review Changes

Review the current uncommitted changes for issues:

1. Run `git diff` to see all changes
2. Check for:
   - Security issues (hardcoded secrets, SQL injection, XSS)
   - Logic errors and missing error handling
   - Type safety issues and missing null checks
   - Performance concerns (N+1 queries, unnecessary re-renders)
3. For each issue found, describe it with file, line number, and suggested fix
4. Run `/verify` to confirm all checks pass

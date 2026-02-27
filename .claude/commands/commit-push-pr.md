# Commit, Push, and Create PR

Run these steps in order:

```bash
git status
git diff --stat
git log --oneline -5
```

1. Stage all changes with `git add -A`
2. Draft a concise commit message based on the diff (1-2 sentences, focus on "why")
3. Commit with the message
4. Push to origin with `git push origin HEAD -u`
5. Check if a PR exists: `gh pr view --json url 2>/dev/null`
   - If no PR exists, create one: `gh pr create --fill`
   - If PR exists, report the URL
6. Output the PR URL

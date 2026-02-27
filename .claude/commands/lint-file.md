# Lint a Single File

Lint and auto-fix the file at $ARGUMENTS.

If it's a `.py` file:
```bash
ruff check --fix "$ARGUMENTS"
ruff format "$ARGUMENTS"
```

If it's a `.ts` or `.tsx` file:
```bash
cd ~/autoapply-web/frontend && bunx eslint --fix "$ARGUMENTS"
cd ~/autoapply-web/frontend && bunx prettier --write "$ARGUMENTS"
```

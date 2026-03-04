# Deploy to Production

Deploy the current build to the EC2 server at ubuntu@52.30.96.169.

1. Run `/verify` first — do NOT deploy if checks fail
2. Build frontend: `cd ~/autoapply-web/frontend && bun run build`
3. Copy backend: `scp -r ~/autoapply-web/backend/ ubuntu@52.30.96.169:~/autoapply-web/backend/`
4. Copy frontend dist: `scp -r ~/autoapply-web/frontend/dist/ ubuntu@52.30.96.169:~/autoapply-web/frontend/dist/`
5. Copy requirements: `scp ~/autoapply-web/requirements.txt ubuntu@52.30.96.169:~/autoapply-web/`
6. Install deps + restart: `ssh ubuntu@52.30.96.169 "cd ~/autoapply-web && pip install -r requirements.txt && sudo systemctl restart autoapply"`
7. Verify health: `ssh ubuntu@52.30.96.169 "curl -s http://localhost:8000/api/health"`
8. Report deployment status

bvrinfra.in Operations Runbook

Check Site Status

Verify container is running:

docker ps

Expected container:

bvrinfra-site

---

Check Website

Local test:

curl localhost

Public test:

https://bvrinfra.in

---

View Logs

docker logs bvrinfra-site

Follow logs:

docker logs -f bvrinfra-site

---

Restart Website

docker restart bvrinfra-site

Verify:

docker ps

---

Stop Website

docker stop bvrinfra-site

---

Start Website

docker start bvrinfra-site

---

Update Website

Navigate to project:

cd /apps/bvrinfra/bvrinfra-site

Pull latest code:

git pull

Build image:

docker build -t bvrinfra-site:v1 .

Restart deployment:

docker compose down
docker compose up -d

Verify:

docker ps

---

DNS Verification

Check:

bvrinfra.in
www.bvrinfra.in

Expected:

Both resolve successfully.

---

SSL Verification

Check:

https://bvrinfra.in

Expected:

Valid certificate and secure connection.

---

Recovery Procedure

1. Check container status
2. Check logs
3. Restart container
4. Rebuild image if required
5. Redeploy application
6. Verify website accessibility

---

Important Locations

Project:

/apps/bvrinfra/bvrinfra-site

Documentation:

~/docs

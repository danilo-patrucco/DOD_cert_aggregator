# DOD_cert_aggregator

Containerized, auto-updated bundle of DoD (Department of Defense) root and intermediate certificates.

## Important Notes

*Very important*

- The certificates are all publicly available files that can be downloaded from Cyber.mil.
- The idea behind this repo is to make sure that the certificates are available quickly and easily (this container can be used in a multi-stage build to plug certs easily).
- Any additional certificate that might be deemed useful can be added with a PR.

This repository:

- Downloads and aggregates DoD certificate ZIPs defined in [`dod_certs.txt`](./dod_certs.txt)
- Stores the extracted certificates in the [`certificates/`](./certificates/) folder
- Builds and publishes a lightweight Alpine-based Docker image to Docker Hub:
  - **Image:** `danilopatrucco1/dodcerts`
  - **Tags:** semantic version tags (`vX.Y.Z`) + `latest`
- Uses GitHub Actions to keep both the **image** and the **Docker Hub description** up to date.

---

## Docker Image

- **Registry:** Docker Hub  
- **Repository:** `danilopatrucco1/dodcerts`  
- **Base image:** `alpine:3.20`  
- **Contents:** Files from this repo’s `certificates/` directory copied into the image at:

```text
/certs/certificates
```

This image does **not** modify the system trust store or install the certificates into `/etc/ssl/certs` or similar.  
It’s meant to be a **data image** you can pull, inspect, or copy certs from as needed.

---

## Pulling and Inspecting the Image

```bash
# Pull the latest image
docker pull danilopatrucco1/dodcerts:latest

# Inspect the certificate files inside the container
docker run --rm -it danilopatrucco1/dodcerts:latest ls -l /certs/certificates
```

To copy the certificates out to your host:

```bash
# Create a temporary container
docker create --name dodcerts_tmp danilopatrucco1/dodcerts:latest

# Copy all certificates to a local folder
docker cp dodcerts_tmp:/certs/certificates ./certificates-from-image

# Clean up the temp container
docker rm dodcerts_tmp
```

---

## How the Automation Works

A GitHub Actions workflow handles:

1. **Certificate refresh**
   - Runs [`download_commit_certs.py`](./download_commit_certs.py)
   - Script reads URLs from [`dod_certs.txt`](./dod_certs.txt), downloads the ZIPs, and updates files in `certificates/`.

2. **Change detection**
   - If `git status` detects changes under version control (e.g., updated certs), the workflow:
     - Commits the changes back to `main`
     - Computes the next **semantic version** tag (`vX.Y.Z`, bumping the patch)
     - Creates and pushes the new tag

3. **Image build & push**
   - Builds a Docker image from [`dockerfile`](./dockerfile)
   - Pushes it to Docker Hub as:
     - `danilopatrucco1/dodcerts:<new-tag>`
     - `danilopatrucco1/dodcerts:latest`

4. **Docker Hub description sync**
   - A job in the same workflow uses [`peter-evans/dockerhub-description`](https://github.com/peter-evans/dockerhub-description) to update the **Docker Hub repo description** from this `README.md`, whenever `README.md` (or the workflow itself) is changed.

---

## GitHub Actions / Configuration

### Secrets

Configure these in **GitHub → Settings → Secrets and variables → Actions → Secrets**:

- `DOCKERHUB_USERNAME`  
  Your Docker Hub username (e.g. `danilopatrucco1`).

- `DOCKERHUB_TOKEN`  
  A Docker Hub password or personal access token with read/write permissions.

### Variables

Configure this in **GitHub → Settings → Secrets and variables → Actions → Variables**:

- `IMAGE_NAME`  

  ```text
  danilopatrucco1/dodcerts
  ```

---

## Local Development

To run the cert aggregation locally:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements
python download_commit_certs.py
```

Certificates will land in the `certificates/` directory.

To build the image locally:

```bash
docker build -t danilopatrucco1/dodcerts:local -f dockerfile .
```

---

## Dockerfile (Overview)

The Docker image is a minimal Alpine container that just carries the aggregated certs:

```dockerfile
FROM alpine:3.20

# Simple data image that just carries the downloaded DoD certs
WORKDIR /certs

# Copy the aggregated certificates into the image
COPY certificates/ ./certificates/
```

---

## License / Disclaimer

This project aggregates and redistributes publicly available DoD certificates for convenience.  
Use at your own risk and verify certificates against official DoD sources before trusting them in production environments.

# DOD_cert_aggregator

Containerized, auto-updated bundle of DoD (Department of Defense) root and intermediate certificates.

## Important Notes

*Very important*

- The certificates are all publicly available files that can be downloaded from Cyber.mil.
- The idea behind this repo is to make sure that the certificates are available quickly and easily (this container can be used in a multi-stage build to plug certs easily).
- Any additional certificate that might be deemed useful can be added with a PR.
- This project is **not** an official DoD, DISA, or Cyber.mil project and is provided as an **unofficial convenience mirror** only.

This repository:

- Downloads and aggregates DoD certificate ZIPs defined in [`dod_certs.txt`](./dod_certs.txt)
- Stores the extracted certificates in the [`certificates/`](./certificates/) folder
- Builds and publishes a lightweight Alpine-based Docker image to Docker Hub:
  - **Image:** `danilopatrucco1/dodcerts`
  - **Tags:** semantic version tags (`vX.Y.Z`) + `latest`
- Uses GitHub Actions to keep both the **image** and the **Docker Hub description** up to date.

The **authoritative source of truth** for these certificates is always the official DoD PKI repositories on Cyber.mil and related DoD-operated endpoints.

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
It’s meant to be a **data image** you can pull, inspect, or copy certs from as needed (for example, in a multi-stage build).

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

## Legal / Policy / Disclaimer

> **Important:** Nothing in this repository or image constitutes legal advice.  
> If you are using this project in a production, government, or contractual context,  
> you are responsible for consulting your own legal and compliance resources.

- The certificates in this project are **publicly available** artifacts retrieved from official DoD PKI endpoints (for example, Cyber.mil).  
  This project does **not** generate or modify the underlying certificate content, other than:
  - format conversions (e.g., PKCS#7 to PEM), and  
  - aggregation into merged PEM files for convenience.

- This repository and container are **unofficial** and are **not affiliated with, endorsed by, or sponsored by**:
  - the U.S. Department of Defense,  
  - DISA,  
  - or Cyber.mil / DoD Cyber Exchange.

- The **authoritative source** for these certificates is always the official DoD PKI repositories.  
  Users of this project should:
  - verify fingerprints and validity against the official sources, and  
  - periodically re-validate that the certificates match current DoD PKI distributions and policies.

- Use of DoD PKI certificates may be subject to the DoD X.509 Certificate Policy, DoD PKI CP/CPS documents, and other applicable regulations and policies.  
  By using this project, **you agree** that:
  - You are solely responsible for ensuring your use of these certificates complies with all applicable laws, regulations, policies, security requirements, and contractual obligations.
  - You will not rely on this repository or image as an official or authoritative source of DoD PKI material.

- These certificates are typically intended for environments that legitimately rely on DoD PKI (e.g., systems performing DoD-related business or interacting with DoD services).  
  They **should not** be treated as generic public CA roots for unrelated or non-DoD use cases.

- This project is provided **“as is”**, without any warranty of any kind, express or implied, including but not limited to:
  - accuracy, completeness, or timeliness of the certificates or metadata,  
  - fitness for a particular purpose,  
  - or security of any system where they are deployed.

- The author(s) of this project:
  - accept **no liability** for any damage, loss, incident, or non-compliance arising from use or misuse of this repository, its artifacts, or any derived works; and  
  - make **no representation** that using this repository or container satisfies any specific compliance framework (including but not limited to DoD, FedRAMP, NIST, or agency-specific controls).

If you are unsure whether you are permitted to use these certificates, or how they may be used in your environment, consult:

1. Your organization’s security/compliance team; and  
2. The official DoD PKI documentation and Cyber.mil resources.


import os
import subprocess
import zipfile
import requests
import shutil
import logging
import sys

# Configure logging
logging.basicConfig(
    filename='logs.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_case_insensitive_collisions(directory: str) -> None:
    seen = {}
    collisions = []
    try:
        entries = os.listdir(directory)
    except FileNotFoundError:
        return
    for name in entries:
        full_path = os.path.join(directory, name)
        if not os.path.isfile(full_path):
            continue
        key = name.lower()
        if key in seen and seen[key] != name:
            collisions.append((seen[key], name))
        else:
            seen[key] = name
    if collisions:
        msg_lines = ["Case-insensitive filename collisions detected in "
                     f"{directory}:"]
        for a, b in collisions:
            msg_lines.append(f"  - {a}  <->  {b}")
        msg = "\n".join(msg_lines)
        print(msg, file=sys.stderr)
        raise RuntimeError(msg)

def detect_p7b_format(path: str) -> str:
    """
    Very simple heuristic:
    - If the file starts with '-----BEGIN', treat as PEM.
    - Otherwise treat as DER.
    """
    try:
        with open(path, 'rb') as f:
            first_bytes = f.read(64)
        if first_bytes.lstrip().startswith(b'-----BEGIN'):
            return 'PEM'
    except Exception as e:
        logging.error(f"Failed to read {path} to detect format: {e}")

    return 'DER'

repo_root_path = os.path.join(os.getcwd(), 'certificates')
download_dir = './downloads'
os.makedirs(download_dir, exist_ok=True)
os.makedirs(repo_root_path, exist_ok=True)
logging.info("Directory setup completed.")

with open('dod_certs.txt', 'r') as file:
    urls = [u.strip() for u in file.readlines() if u.strip()]

for url in urls:
    try:
        logging.info(f"Downloading {url}")
        response = requests.get(url)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        continue

    zip_path = os.path.join(download_dir, os.path.basename(url))
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    logging.info(f"Downloaded {url} to {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_dir)
        logging.info(f"Extracted ZIP file from {zip_path}")
    except zipfile.BadZipFile as e:
        logging.error(f"Bad ZIP file {zip_path}: {e}")
        continue

for root, dirs, files in os.walk(download_dir):
    pem_files = []

    relative_path = root[len(download_dir):].strip(os.sep).replace(os.sep, '_')
    identifier = relative_path.split('_')[-1] if relative_path else 'root'

    for file in files:
        if file.endswith('.p7b'):
            p7b_path = os.path.join(root, file)
            pem_path = p7b_path.replace('.p7b', '.pem')

            inform = detect_p7b_format(p7b_path)
            cmd = [
                'openssl', 'pkcs7',
                '-inform', inform,
                '-in', p7b_path,
                '-outform', 'PEM',
                '-print_certs',
                '-out', pem_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                pem_files.append(pem_path)
                logging.info(f"Converted {p7b_path} ({inform}) to {pem_path}")
            else:
                logging.error(
                    f"Failed to convert {p7b_path} ({inform}). "
                    f"Return code: {result.returncode}, stderr: {result.stderr}"
                )

        elif file.endswith('.cer'):
            cer_path = os.path.join(root, file)
            pem_path = cer_path.replace('.cer', '.pem')
            cmd = [
                'openssl', 'x509',
                '-in', cer_path,
                '-out', pem_path,
                '-outform', 'PEM'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                pem_files.append(pem_path)
                logging.info(f"Converted {cer_path} to {pem_path}")
            else:
                logging.error(
                    f"Failed to convert {cer_path}. "
                    f"Return code: {result.returncode}, stderr: {result.stderr}"
                )
    if pem_files:
        merged_pem_path = os.path.join(root, f'merged_certs_{identifier}.pem')
        with open(merged_pem_path, 'wb') as merged_file:
            for pem_file in pem_files:
                try:
                    with open(pem_file, 'rb') as pf:
                        merged_file.write(pf.read())
                    logging.info(f"Merged {pem_file} into {merged_pem_path}")
                except Exception as e:
                    logging.error(f"Failed to merge {pem_file}: {e}")

        logging.info(f"Merged PEM files into {merged_pem_path}")
        try:
            shutil.copy(merged_pem_path, repo_root_path)
            logging.info(f"Copied {merged_pem_path} to {repo_root_path}")
        except Exception as e:
            logging.error(f"Failed to copy {merged_pem_path} to {repo_root_path}: {e}")
try:
    shutil.rmtree(download_dir)
    logging.info("Download directory removed.")
except Exception as e:
    logging.error(f"Failed to remove download directory {download_dir}: {e}")

# 🔍 New: case-insensitive collision check in certificates/
try:
    check_case_insensitive_collisions(repo_root_path)
    logging.info("No case-insensitive filename collisions detected in certificates.")
except RuntimeError as e:
    logging.error(str(e))
    sys.exit(1)

# Verify each PEM is a valid X.509 cert
for pem_file in os.listdir(repo_root_path):
    if pem_file.endswith('.pem'):
        pem_path = os.path.join(repo_root_path, pem_file)
        result = subprocess.run(
            ['openssl', 'x509', '-in', pem_path, '-noout'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logging.info(f"Verified certificate {pem_path} successfully.")
        else:
            logging.error(
                f"Verification failed for certificate {pem_path}. "
                f"Return code: {result.returncode}, stderr: {result.stderr}"
            )

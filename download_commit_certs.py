import os
import subprocess
import zipfile
import requests
import shutil
import logging
import sys
import base64
import hashlib

# Configure logging
logging.basicConfig(
    filename='logs.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def check_case_insensitive_collisions(directory: str) -> None:
    try:
        entries = [
            name for name in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, name))
        ]
    except FileNotFoundError:
        return
    groups = {}
    for name in entries:
        key = name.lower()
        groups.setdefault(key, []).append(name)
    used_lower = {name.lower() for name in entries}

    for key, names in groups.items():
        if len(names) <= 1:
            continue
        names.sort()
        canonical = names[0]

        logging.warning(
            "Case-insensitive filename collisions detected in %s: %s",
            directory,
            ", ".join(names),
        )
        for idx, colliding_name in enumerate(names[1:], start=1):
            base, ext = os.path.splitext(colliding_name)
            suffix = idx
            while True:
                new_name = f"{base}_{suffix}{ext}"
                new_key = new_name.lower()
                new_path = os.path.join(directory, new_name)
                if new_key not in used_lower and not os.path.exists(new_path):
                    break
                suffix += 1
            old_path = os.path.join(directory, colliding_name)
            os.rename(old_path, new_path)
            used_lower.add(new_name.lower())
            logging.info(
                "Renamed %s -> %s to avoid case-insensitive collision with %s",
                colliding_name,
                new_name,
                canonical,
            )


def detect_p7b_format(path: str) -> str:
    try:
        with open(path, 'rb') as f:
            first_bytes = f.read(64)
        if first_bytes.lstrip().startswith(b'-----BEGIN'):
            return 'PEM'
    except Exception as e:
        logging.error(f"Failed to read {path} to detect format: {e}")
    return 'DER'


def split_pem_file(path: str):
    """
    Yield each certificate block from a PEM file as a string.
    """
    if not os.path.exists(path):
        return

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            block = []
            in_cert = False
            for line in f:
                if 'BEGIN CERTIFICATE' in line:
                    in_cert = True
                    block = [line]
                elif 'END CERTIFICATE' in line and in_cert:
                    block.append(line)
                    yield ''.join(block)
                    in_cert = False
                    block = []
                elif in_cert:
                    block.append(line)
    except Exception as e:
        logging.error(f"Failed to split PEM file {path}: {e}")


def cert_der_sha256(pem_block: str) -> str:
    """
    Convert a PEM cert block to DER & return SHA256 hex digest.
    """
    lines = [
        l.strip()
        for l in pem_block.splitlines()
        if 'BEGIN CERTIFICATE' not in l
        and 'END CERTIFICATE' not in l
        and l.strip()
    ]
    der = base64.b64decode(''.join(lines))
    return hashlib.sha256(der).hexdigest()


repo_root_path = os.path.join(os.getcwd(), 'certificates')
download_dir = './downloads'
os.makedirs(download_dir, exist_ok=True)
os.makedirs(repo_root_path, exist_ok=True)
logging.info("Directory setup completed.")

# Read URLs from dod_certs.txt
with open('dod_certs.txt', 'r') as file:
    urls = [u.strip() for u in file.readlines() if u.strip()]

# Download and extract ZIPs
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

# Process .p7b and .cer files
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

    # Merge PEM files with deduplication
    if pem_files:
        merged_pem_path = os.path.join(root, f'merged_certs_{identifier}.pem')
        try:
            seen = set()
            unique_count = 0
            with open(merged_pem_path, 'w', encoding='utf-8') as merged_file:
                for pem_file in pem_files:
                    for cert_block in split_pem_file(pem_file):
                        if not cert_block:
                            continue
                        try:
                            fp = cert_der_sha256(cert_block)
                        except Exception as e:
                            logging.error(f"Failed to fingerprint cert from {pem_file}: {e}")
                            continue

                        if fp in seen:
                            # Duplicate cert, skip
                            continue
                        seen.add(fp)
                        unique_count += 1

                        merged_file.write(cert_block)
                        if not cert_block.endswith('\n'):
                            merged_file.write('\n')
                        merged_file.write('\n')  # separate certs

                logging.info(
                    f"Merged {len(pem_files)} PEM files into {merged_pem_path} "
                    f"with {unique_count} unique certificates"
                )
        except Exception as e:
            logging.error(f"Failed to create merged PEM file {merged_pem_path}: {e}")
            merged_pem_path = None

        # Copy merged file to repo_root_path
        if merged_pem_path and os.path.isfile(merged_pem_path):
            try:
                shutil.copy(merged_pem_path, repo_root_path)
                logging.info(f"Copied {merged_pem_path} to {repo_root_path}")
            except Exception as e:
                logging.error(f"Failed to copy {merged_pem_path} to {repo_root_path}: {e}")

# Cleanup downloads
try:
    shutil.rmtree(download_dir)
    logging.info("Download directory removed.")
except Exception as e:
    logging.error(f"Failed to remove download directory {download_dir}: {e}")

# Fix case-insensitive collisions in certificates dir
check_case_insensitive_collisions(repo_root_path)
logging.info("Case-insensitive filename collisions (if any) have been resolved.")

# Verify PEM certificates (first cert in each file)
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

print("Download and processing complete. Certificates are in ./certificates")

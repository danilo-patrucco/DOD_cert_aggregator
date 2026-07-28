import os
import re
import subprocess
import zipfile
import requests
import shutil
import logging
import sys
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

CERT_BLOCK_RE = re.compile(rb'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', re.S)
MAX_MERGED_FILE_BYTES = 65536

def split_certificates(data: bytes) -> list:
    return CERT_BLOCK_RE.findall(data)

def write_cert_chunks(certs: list, base_path: str, max_bytes: int = MAX_MERGED_FILE_BYTES) -> list:
    chunks = []
    current_chunk = []
    current_size = 0
    for cert in certs:
        if current_chunk and current_size + len(cert) > max_bytes:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0
        current_chunk.append(cert)
        current_size += len(cert)
    if current_chunk:
        chunks.append(current_chunk)

    if len(chunks) > 1:
        paths = [f"{base_path}_{idx}.pem" for idx in range(1, len(chunks) + 1)]
    else:
        paths = [f"{base_path}.pem"]

    for path, chunk in zip(paths, chunks):
        with open(path, 'wb') as f:
            for cert in chunk:
                f.write(cert)
        if len(chunk) == 1 and len(chunk[0]) > max_bytes:
            logging.warning(
                "Certificate written to %s (%d bytes) exceeds %d bytes on its own; cannot split further.",
                path, len(chunk[0]), max_bytes,
            )
    return paths

def remove_duplicate_pem_files(directory: str) -> None:
    try:
        entries = [
            name for name in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, name))
            and name.endswith('.pem')
        ]
    except FileNotFoundError:
        return

    hash_map = {}

    for name in sorted(entries):
        path = os.path.join(directory, name)
        try:
            with open(path, 'rb') as f:
                data = f.read()
            file_hash = hashlib.sha256(data).hexdigest()
        except Exception as e:
            logging.error(f"Failed to hash PEM file {path}: {e}")
            continue

        if file_hash in hash_map:
            original = hash_map[file_hash]
            logging.info(
                "File %s is content-identical to %s in %s; removing duplicate.",
                name,
                original,
                directory,
            )
            try:
                os.remove(path)
            except Exception as e:
                logging.error(f"Failed to remove duplicate file {path}: {e}")
        else:
            hash_map[file_hash] = name


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

seen_cert_hashes = set()
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
        merged_base_path = os.path.join(root, f'merged_certs_{identifier}')
        unique_certs = []
        for pem_file in pem_files:
            try:
                with open(pem_file, 'rb') as pf:
                    data = pf.read()
                for cert in split_certificates(data):
                    cert_hash = hashlib.sha256(cert).hexdigest()
                    if cert_hash in seen_cert_hashes:
                        continue
                    seen_cert_hashes.add(cert_hash)
                    unique_certs.append(cert + b'\n')
                logging.info(f"Collected unique certs from {pem_file} for {merged_base_path}")
            except Exception as e:
                logging.error(f"Failed to merge {pem_file}: {e}")

        merged_paths = []
        if unique_certs:
            try:
                merged_paths = write_cert_chunks(unique_certs, merged_base_path)
                logging.info(f"Wrote {len(merged_paths)} merged PEM file(s) for {merged_base_path}")
            except Exception as e:
                logging.error(f"Failed to write merged PEM file(s) for {merged_base_path}: {e}")
                merged_paths = []

        stale_pattern = re.compile(
            re.escape(f'merged_certs_{identifier}') + r'(_\d+)?\.pem$'
        )
        expected_names = {os.path.basename(p) for p in merged_paths}
        try:
            for name in os.listdir(repo_root_path):
                if stale_pattern.fullmatch(name) and name not in expected_names:
                    os.remove(os.path.join(repo_root_path, name))
                    logging.info(f"Removed stale merged file {name} from {repo_root_path}")
        except Exception as e:
            logging.error(f"Failed to clean stale merged files for {identifier} in {repo_root_path}: {e}")

        for merged_pem_path in merged_paths:
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

check_case_insensitive_collisions(repo_root_path)
logging.info("Case-insensitive filename collisions (if any) have been resolved.")
remove_duplicate_pem_files(repo_root_path)
logging.info("Duplicate PEM files (by content) have been removed from ./certificates.")

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

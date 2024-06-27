import os
import subprocess
import zipfile
import requests
import shutil
import logging

# Setup logging
logging.basicConfig(filename='logs.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Directory setup
repo_root_path = os.path.join(os.getcwd(), 'certificates')
download_dir = './downloads'
os.makedirs(download_dir, exist_ok=True)
os.makedirs(repo_root_path, exist_ok=True)
logging.info("Directories set up successfully.")

# Read URLs from the dod_cert.txt file
with open('dod_certs.txt', 'r') as file:
    urls = file.readlines()

# Download the zip files
for url in urls:
    url = url.strip()
    response = requests.get(url)
    zip_path = os.path.join(download_dir, os.path.basename(url))
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    logging.info(f"Downloaded {url} to {zip_path}")

    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)
    logging.info(f"Extracted {zip_path}")

# Process .p7b and .cer files in the directory
for root, dirs, files in os.walk(download_dir):
    pem_files = []
    for file in files:
        if file.endswith('.p7b'):
            p7b_path = os.path.join(root, file)
            pem_path = p7b_path.replace('.p7b', '.pem')
            pem_files.append(pem_path)
            # Convert p7b to pem
            result = subprocess.run(['openssl', 'pkcs7', '-inform', 'DER', '-in', p7b_path, '-print_certs', '-outform', 'PEM', '-out', pem_path])
            if result.returncode == 0:
                logging.info(f"Converted {p7b_path} to {pem_path}")
            else:
                logging.error(f"Failed to convert {p7b_path}")

        elif file.endswith('.cer'):
            cer_path = os.path.join(root, file)
            pem_path = cer_path.replace('.cer', '.pem')
            pem_files.append(pem_path)
            # Convert cer to pem
            result = subprocess.run(['openssl', 'x509', '-in', cer_path, '-out', pem_path, '-outform', 'PEM'])
            if result.returncode == 0:
                logging.info(f"Converted {cer_path} to {pem_path}")
            else:
                logging.error(f"Failed to convert {cer_path}")

    # Merge all pem files in the directory
    if pem_files:
        merged_pem_path = os.path.join(root, f'merged_certs_{identifier}.pem')
        with open(merged_pem_path, 'wb') as merged_file:
            for pem_file in pem_files:
                with open(pem_file, 'rb') as pf:
                    merged_file.write(pf.read())
        logging.info(f"Merged PEM files at {merged_pem_path}")

    # Move processed files to the root of the repository
    if pem_files:
        subprocess.run(['cp', merged_pem_path, repo_root_path])
        logging.info(f"Copied {merged_pem_path} to {repo_root_path}")

# Verify PEM certificates
for pem_file in os.listdir(repo_root_path):
    if pem_file.endswith('.pem'):
        pem_path = os.path.join(repo_root_path, pem_file)
        logging.info(f"Verifying {pem_file}")
        subprocess.run(['openssl', 'x509', '-in', pem_path, '-text', '-noout'])

# Remove downloads dir 
shutil.rmtree(download_dir)
logging.info("Cleaned up download directory.")

# Commit the changes to the local repository
subprocess.run(['git', '-C', repo_root_path, 'add', '.'])
subprocess.run(['git', '-C', repo_root_path, 'commit', '-m', 'Add updated PEM files'])
logging.info("Changes committed to the local repository.")

print("Download and processing complete. Changes committed locally.")

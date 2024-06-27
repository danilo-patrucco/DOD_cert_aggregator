import os
import subprocess
import zipfile
import requests
import shutil
import logging

# Configure logging
logging.basicConfig(filename='logs.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Directory setup
repo_root_path = os.path.join(os.getcwd(), 'certificates')
download_dir = './downloads'
os.makedirs(download_dir, exist_ok=True)
os.makedirs(repo_root_path, exist_ok=True)
logging.info("Directory setup completed.")

# Read URLs from the dod_certs.txt file
with open('dod_certs.txt', 'r') as file:
    urls = file.readlines()

# Download the zip files
for url in urls:
    url = url.strip()
    response = requests.get(url)
    zip_path = os.path.join(download_dir, os.path.basename(url))
    with open(zip_path, 'wb') as f:
        f.write(response.content)
    logging.info(f"Downloaded {url}")

    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)
    logging.info(f"Extracted ZIP file from {zip_path}")

# Process .p7b and .cer files in the directory
for root, dirs, files in os.walk(download_dir):
    pem_files = []
    # Create a meaningful name from the path
    relative_path = root[len(download_dir):].strip(os.sep).replace(os.sep, '_')
    identifier = relative_path.split('_')[-1]

    for file in files:
        if file.endswith('.p7b'):
            p7b_path = os.path.join(root, file)
            pem_path = p7b_path.replace('.p7b', '.pem')
            pem_files.append(pem_path)
            # Convert p7b to pem
            result = subprocess.run(['openssl', 'pkcs7', '-inform', 'DER', '-in', p7b_path, '-outform', 'PEM', '-out', pem_path])
            logging.info(f"convertion result: {result}")
            logging.info(f"Converted {p7b_path} to PEM")
        elif file.endswith('.cer'):
            cer_path = os.path.join(root, file)
            pem_path = cer_path.replace('.cer', '.pem')
            # Convert cer to pem
            result = subprocess.run(['openssl', 'x509', '-in', cer_path, '-out', pem_path, '-outform', 'PEM'], capture_output=True, text=True)
            if result.returncode == 0:
                pem_files.append(pem_path)
                logging.info(f"Converted {cer_path} to PEM")
            else:
                logging.error(f"Failed to convert {cer_path}. Error: {result.stderr}")

    # Merge all pem files in the directory
    if pem_files:
        merged_pem_path = os.path.join(root, f'merged_certs_{identifier}.pem')
        with open(merged_pem_path, 'wb') as merged_file:
            for pem_file in pem_files:
                with open(pem_file, 'rb') as pf:
                    merged_file.write(pf.read())
        logging.info(f"Merged PEM files into {merged_pem_path}")

    # Move processed files to the root of the repository
    if pem_files:
        subprocess.run(['cp', merged_pem_path, repo_root_path])
        logging.info(f"Moved {merged_pem_path} to {repo_root_path}")

# Remove downloads dir 
shutil.rmtree(download_dir)
logging.info("Download directory removed.")

# Verify PEM certificates
for pem_file in os.listdir(repo_root_path):
    if pem_file.endswith('.pem'):
        pem_path = os.path.join(repo_root_path, pem_file)
        result = subprocess.run(['openssl', 'x509', '-in', pem_path, '-noout'], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Verified certificate {pem_path} successfully.")
        else:
            logging.error(f"Verification failed for certificate {pem_path}. Error: {result.stderr}")

# Commit the changes to the local repository
subprocess.run(['git', '-C', repo_root_path, 'add', '.'])
subprocess.run(['git', '-C', repo_root_path, 'commit', '-m', 'Add updated PEM files'])
logging.info("Changes committed to the local repository.")

print("Download and processing complete. Changes committed locally.")

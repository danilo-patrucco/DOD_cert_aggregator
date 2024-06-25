import os
import subprocess
import zipfile
import requests

# Directory setup
download_dir = './downloads'
os.makedirs(download_dir, exist_ok=True)

# Read URLs from the dod_cert.txt file
with open('dod_cert.txt', 'r') as file:
    urls = file.readlines()

# Download the zip files
for url in urls:
    url = url.strip()
    response = requests.get(url)
    zip_path = os.path.join(download_dir, os.path.basename(url))
    with open(zip_path, 'wb') as f:
        f.write(response.content)

    # Extract the zip file
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)

# Convert .p7b files to .pem and merge them
for root, dirs, files in os.walk(download_dir):
    pem_files = []
    for file in files:
        if file.endswith('.p7b'):
            p7b_path = os.path.join(root, file)
            pem_path = p7b_path.replace('.p7b', '.pem')
            pem_files.append(pem_path)
            # Convert p7b to pem
            subprocess.run(['openssl', 'pkcs7', '-inform', 'DER', '-in', p7b_path,
                            '-print_certs', '-outform', 'PEM', '-out', pem_path])

    # Merge all pem files in the directory
    if pem_files:
        merged_pem_path = os.path.join(root, 'merged_certs.pem')
        with open(merged_pem_path, 'wb') as merged_file:
            for pem_file in pem_files:
                with open(pem_file, 'rb') as pf:
                    merged_file.write(pf.read())

        # Move merged pem file to the root of the repository
        repo_root_path = '/Users/danilo.patrucco/repositories/gitlab/chart/charts/certmanager-issuer'
        subprocess.run(['cp', merged_pem_path, repo_root_path])

# Commit the changes to the local repository
subprocess.run(['git', '-C', repo_root_path, 'add', '.'])
subprocess.run(['git', '-C', repo_root_path, 'commit', '-m', 'Add updated PEM files'])

print("Download and processing complete. Changes committed locally.")

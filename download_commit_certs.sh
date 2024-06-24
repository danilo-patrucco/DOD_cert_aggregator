#!/bin/bash

# Directory where zip files will be downloaded and extracted
download_directory="downloads"
mkdir -p "$download_directory"
cd "$download_directory"

# File containing URLs to download
url_file="dod_certs.txt"

# Read each line in the file as a URL
while IFS= read -r url
do
    echo "Downloading and extracting from $url"
    # Use basename to derive a filename from the URL
    file_name=$(basename "$url")

    # Download the file
    curl -O "$url"

    # Unzip the file
    unzip "$file_name"
done < "../$url_file"

# Move to the repository root
cd ..

# Git commands to add, commit, and push changes
git add .
git commit -m "Updated certificates and scripts"

echo "All tasks completed."

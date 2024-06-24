#!/bin/bash

# Directory where zip files will be downloaded and extracted
download_directory="downloads"
mkdir -p "$download_directory"
cd "$download_directory"

# File containing URLs to download
url_file="../dod_certs.txt"  # Adjust this path to the actual location of your URL file

# Read each line in the file as a URL
while IFS= read -r url
do
    if [[ -z "$url" ]]; then
        continue  # Skip empty lines
    fi
    echo "Processing $url"
    # Use basename to derive a filename from the URL
    file_name=$(basename "$url")

    # Download the file
    if curl -O "$url"; then
        echo "Downloaded $file_name successfully."
    else
        echo "Failed to download $file_name. Skipping."
        continue
    fi

    # Unzip the file
    if unzip -o "$file_name"; then
        echo "Unzipped $file_name successfully."
    else
        echo "Failed to unzip $file_name. Skipping."
        continue
    fi
done < "$url_file"

# Move to the repository root
cd ..

# Git commands to add, commit, and push changes
git add .
if git commit -m "Updated certificates and scripts"; then
    echo "Committed changes successfully."
else
    echo "No changes to commit."
fi

echo "All tasks completed."

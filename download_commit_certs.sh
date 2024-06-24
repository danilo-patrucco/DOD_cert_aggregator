#!/bin/bash

# Set repository path
REPO_PATH=$1
URL_FILE="dod_certs.txt"

# Create a temporary directory for downloads
TEMP_DIR=$(mktemp -d)

# Function to clean up temporary directory
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Read URLs from the text file
if [ ! -f "$URL_FILE" ]; then
    echo "URL file not found!"
    exit 1
fi

# Download and unzip files
while IFS= read -r URL; do
    if [[ -n "$URL" ]]; then
        FILENAME=$(basename "$URL")
        (cd "$TEMP_DIR" && curl -LO "$URL")
        unzip -q "$TEMP_DIR/$FILENAME" -d "$TEMP_DIR"
    fi
done < "$URL_FILE"

# Move unzipped files to the repository
mv "$TEMP_DIR"/* "$REPO_PATH"

# Change to repository directory
cd "$REPO_PATH" || exit

# Check if there are changes to commit
if [ -n "$(git status --porcelain)" ]; then
    # Stage all changes
    git add .

    # Commit the changes
    git commit -m "Downloaded and unzipped files from URLs in dod_certs.txt and updated repository"

    # Push the changes (optional, requires remote repository configuration)
else
    echo "No changes to commit"
fi
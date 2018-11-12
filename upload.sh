#!/usr/bin/env bash

if [[ $# -eq 0 ]]
  then
    echo "Please provide image source directory file path"
    exit 0
fi

if [[ ! -d "$1" ]]; then
  echo "$1 does not exist; are you sure this is the full file path?"
  exit 1
fi

# Upload Slides
docker cp $1/. ca-load:/data/images/

# Load to Database
for file in $1/*.svs; do
    slide="$(basename "$file")"
    echo $slide
    docker exec -it ca-load python3 /var/www/upload.py "$slide" "/data/images/"
done
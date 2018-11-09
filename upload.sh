#!/usr/bin/env bash

# TODO: request local dir param

# Upload Slides
docker cp ~/slides/. ca-load:/data/images/

# Load to Database
for file in ~/slides/*.svs; do
    slide="$(basename "$file")"
    echo $slide
    docker exec -it ca-load python3 /var/www/upload.py "$slide" "/data/images/"
done
lib_path=$(find /usr/local/lib/ -name 'libopenslide.so.1' -print -quit)

# Check if libopenslide.so.1 is found
if [ -n "$lib_path" ]; then
    # Navigate to the directory containing libopenslide.so.1
    cd "$(dirname "$lib_path")"

    # copy from libopenslide.so.1 to libopenslide.so.0, and /usr/local/lib directly
    cp libopenslide.so.1 libopenslide.so.0 || true
    cp libopenslide.so.1 /usr/local/lib/libopenslide.so.0 || true
else
    echo "libopenslide.so.1 not found in /usr/local/lib/"
fi

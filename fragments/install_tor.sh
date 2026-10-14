#!/usr/bin/env bash
set -e

# Define the absolute path for the local build output
BUILD_DIR="$(pwd)/build"
mkdir -p "$BUILD_DIR"

echo "[*] Cleaning up any previous source directories..."
rm -rf tor-src

echo "[*] Cloning the Tor source repository..."
git clone --depth 1 https://gitlab.com/torproject/tor.git tor-src
cd tor-src

echo "[*] Generating build configuration..."
./autogen.sh

echo "[*] Configuring Tor to build into: $BUILD_DIR"
# --prefix shifts the installation directory from /usr/local to your custom folder
./configure --prefix="$BUILD_DIR" --disable-asciidoc --disable-seccomp

echo "[*] Compiling Tor (using all available CPU cores)..."
make -j$(nproc)

echo "[*] Placing binary and assets into the local folder..."
# This copies the compiled files into your tor_local_build folder instead of the system
make install

cd ..
echo "[+] Build complete!"
echo "[+] Your local Tor binary is available at: $BUILD_DIR/bin/tor"
echo "[*] Verifying execution:"
"$BUILD_DIR/bin/tor" --version

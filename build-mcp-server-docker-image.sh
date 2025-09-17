#!/bin/bash
set -eo pipefail

Dockerfile_PATH="./Dockerfile.MCP-Server"
IMAGE_NAME="call518/mcp-server-openstack-ops"

echo "=== Building OpenStack SDK Release-specific Docker images ==="
echo "Reference: https://releases.openstack.org/teams/openstacksdk.html"

# OpenStack Release to SDK Version Mapping
# Based on https://releases.openstack.org/teams/openstacksdk.html
declare -A OPENSTACK_RELEASES=(
    # Current and Stable releases
    ["flamingo"]="4.5.0,4.7.1"      # Flamingo (2025.2) - Future
    ["epoxy"]="4.1.0,4.4.0"         # Epoxy (2025.1) - Current  
    ["dalmatian"]="3.1.0,4.0.1"     # Dalmatian (2024.2) - Stable
    ["caracal"]="2.0.0,3.0.0"       # Caracal (2024.1) - Stable
    ["bobcat"]="1.1.0,1.5.1"        # Bobcat (2023.2) - Stable
    
    # Supported and Extended Support releases
    ["antelope"]="0.103.0,1.0.2"    # Antelope (2023.1) - Supported
    ["zed"]="0.99.0,0.101.0"        # Zed (2022.2) - Extended Support
    ["yoga"]="0.60.0,0.62.0"        # Yoga (2022.1) - Extended Support
    
    # EOL releases (commented out - uncomment if needed)
    # ["xena"]="0.56.0,0.59.0"        # Xena (2021.2) - EOL
    # ["wallaby"]="0.51.0,0.55.1"     # Wallaby (2021.1) - EOL
    # ["victoria"]="0.47.0,0.50.0"    # Victoria (2020.2) - EOL
    # ["ussuri"]="0.37.0,0.46.1"      # Ussuri (2020.1) - EOL
    # ["train"]="0.28.0,0.36.5"       # Train (2019.2) - EOL
    # ["stein"]="0.18.0,0.27.1"       # Stein (2019.1) - EOL
)

# Build images for each OpenStack release
for release in "${!OPENSTACK_RELEASES[@]}"; do
    version_range="${OPENSTACK_RELEASES[$release]}"
    min_version="${version_range%,*}"
    max_version="${version_range#*,}"
    
    echo
    echo "=== Building ${IMAGE_NAME}:${release} ==="
    echo "OpenStack Release: $(echo $release | tr '[:lower:]' '[:upper:]')"
    echo "SDK Version Range: ${min_version} - ${max_version}"
    
    # Build image with SDK version range as build argument
    docker build \
        --build-arg OPENSTACK_SDK_MIN="${min_version}" \
        --build-arg OPENSTACK_SDK_MAX="${max_version}" \
        --build-arg OPENSTACK_RELEASE="${release}" \
        -t "${IMAGE_NAME}:${release}" \
        -f "${Dockerfile_PATH}" .
    
    echo "✅ Built: ${IMAGE_NAME}:${release}"
done

echo
echo "=== Build Summary ==="
echo "Built images:"
for release in "${!OPENSTACK_RELEASES[@]}"; do
    echo "  - ${IMAGE_NAME}:${release}"
done

echo
echo "Pushing all images to Docker Hub..."
for release in "${!OPENSTACK_RELEASES[@]}"; do
    echo "Pushing ${IMAGE_NAME}:${release}..."
    docker push "${IMAGE_NAME}:${release}"
done
echo "✅ All images pushed successfully!"

# Sets up QEMU for emulating different architectures on your build machine
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Creates a builder instance for multi-architecture builds
docker buildx create --name multiarch --driver docker-container --use

# Builds and pushes images for ARM v7, ARM64, and AMD64
docker buildx build --push --platform linux/arm/v7,linux/arm64/v8,linux/amd64 --tag matthuisman/samsung-tvplus-for-channels .
#!/usr/bin/env bash
set -euo pipefail

# Ubuntu/Debian bootstrap for a GCP Compute Engine VM.
# Run once on a fresh VM:
#   bash scripts/gcp-vm-install-docker.sh

# Select the official repository for the installed distribution.
. /etc/os-release
case "$ID" in
  ubuntu) docker_distro=ubuntu; docker_codename="${UBUNTU_CODENAME:-$VERSION_CODENAME}" ;;
  debian) docker_distro=debian; docker_codename="$VERSION_CODENAME" ;;
  *) echo "Only Ubuntu and Debian are supported." >&2; exit 1 ;;
esac

sudo apt-get update
sudo apt-get install -y ca-certificates curl git

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL "https://download.docker.com/linux/$docker_distro/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$docker_distro \
  $docker_codename stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker

if ! groups "$USER" | grep -q '\bdocker\b'; then
  sudo usermod -aG docker "$USER"
  echo "Docker installed. Log out and back in so your user can run docker without sudo."
else
  echo "Docker installed."
fi

#!/bin/sh
# Download the BEAM-100K split (about 5.4 MB) into data/.
set -e
cd "$(dirname "$0")/.."
mkdir -p data
curl -sL -o data/beam-100k.parquet \
  "https://huggingface.co/datasets/Mohammadta/BEAM/resolve/main/data/100K-00000-of-00001.parquet"
shasum -a 256 data/beam-100k.parquet

#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Assemblage du fichier unique NEXUS OS BUILDER v9.1
# ═══════════════════════════════════════════════════════════════════════════════
# Usage : bash assemble.sh
# Produit : nexus_os_builder_v9_1.py
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

OUT="nexus_os_builder_v9_1.py"
PARTS=(
  "part1.py"   # header, imports, config, SystemUtils
  "part2.py"   # Recipe system, FeatureDetector, Resolver
  "part3.py"   # Downloader, ImageGenerators
  "part4.py"   # OSProject, RootFSAssembler
  "part5.py"   # CPIOBuilder, KernelManager, BootImageBuilder, OSFactory
  "part6.py"   # HTML, Handler, Server, main
)

rm -f "$OUT"

for part in "${PARTS[@]}"; do
  if [ ! -f "$part" ]; then
    echo "MANQUANT: $part"
    exit 1
  fi
  cat "$part" >> "$OUT"
  echo "" >> "$OUT"
done

echo "Assemblé: $OUT"
wc -l "$OUT"

echo ""
echo "Vérification syntaxe..."
python3 -m py_compile "$OUT" && echo "OK — syntaxe valide"

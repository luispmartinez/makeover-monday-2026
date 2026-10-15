#!/bin/sh
# Downloads the three open-source (OFL) fonts the canvas script needs into ./fonts
set -e
mkdir -p fonts
B=https://raw.githubusercontent.com/google/fonts/main/ofl
curl -L -o fonts/Anton-Regular.ttf                 $B/anton/Anton-Regular.ttf
curl -L -o fonts/BarlowCondensed-Medium.ttf        $B/barlowcondensed/BarlowCondensed-Medium.ttf
curl -L -o fonts/BarlowCondensed-SemiBold.ttf      $B/barlowcondensed/BarlowCondensed-SemiBold.ttf
curl -L -o fonts/OpenSans-Regular.ttf              "$B/opensans/OpenSans%5Bwdth%2Cwght%5D.ttf"

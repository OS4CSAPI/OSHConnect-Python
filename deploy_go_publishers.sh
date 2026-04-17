#!/bin/bash
# deploy_go_publishers.sh — Deploy updated publisher code and set up Go server publishers on VM
set -e

SRC=/tmp/OSHConnect-Python/publishers
HOME_DIR=/home/ubuntu
GO_URL="https://129-80-248-53.sslip.io/csapi-go"

echo "=== Updating existing publisher directories ==="

declare -A PUBS=(
  [nws-publisher]=nws
  [ndbc-publisher]=ndbc
  [coops-publisher]=coops
  [usgs-water-publisher]=usgs_water
  [usgs-nims-publisher]=usgs_nims
  [usgs-eq-publisher]=usgs_eq
)

for dir_name in "${!PUBS[@]}"; do
  pub=${PUBS[$dir_name]}
  target=$HOME_DIR/$dir_name/publishers
  if [ -d "$target" ]; then
    cp -f $SRC/__init__.py $target/
    cp -f $SRC/bootstrap_helpers.py $target/
    cp -rf $SRC/$pub/* $target/$pub/
    echo "  Updated $dir_name ($pub)"
  else
    echo "  SKIP $dir_name (not found)"
  fi
done

# Update opensky (in OSHConnect-Python dir)
if [ -d "$HOME_DIR/OSHConnect-Python/publishers/opensky" ]; then
  cp -f $SRC/__init__.py $HOME_DIR/OSHConnect-Python/publishers/
  cp -f $SRC/bootstrap_helpers.py $HOME_DIR/OSHConnect-Python/publishers/
  cp -rf $SRC/opensky/* $HOME_DIR/OSHConnect-Python/publishers/opensky/
  echo "  Updated OSHConnect-Python (opensky)"
fi

echo ""
echo "=== Creating Go publisher directories ==="

# Create Go publisher directories for publishers that don't have one yet
# (usgs-eq and opensky already have Go services)
declare -A GO_PUBS=(
  [nws-publisher-go]=nws
  [ndbc-publisher-go]=ndbc
  [coops-publisher-go]=coops
  [aviation-wx-publisher-go]=aviation_wx
  [usgs-water-publisher-go]=usgs_water
  [usgs-nims-publisher-go]=usgs_nims
  [iss-publisher-go]=iss
)

for dir_name in "${!GO_PUBS[@]}"; do
  pub=${GO_PUBS[$dir_name]}
  target=$HOME_DIR/$dir_name/publishers
  mkdir -p $target/$pub
  cp -f $SRC/__init__.py $target/
  cp -f $SRC/bootstrap_helpers.py $target/
  cp -f $SRC/base.py $target/ 2>/dev/null || true
  cp -rf $SRC/$pub/* $target/$pub/
  echo "  Created $dir_name ($pub)"
done

# Aviation WX also needs to be updated in the existing SH directory
# (it doesn't have one — check)
if [ ! -d "$HOME_DIR/aviation-wx-publisher" ]; then
  echo "  Note: No existing aviation-wx-publisher SH directory found"
fi

echo ""
echo "=== Running bootstraps against Go server ==="

# Run each bootstrap against the Go server
export OSH_ADDRESS=129-80-248-53.sslip.io
export OSH_PORT=443
export OSH_USER=os4csapi
export OSH_PASS=ogc134mm
export OSH_BASE_URL=$GO_URL

# NWS bootstrap
echo "-- NWS Bootstrap --"
cd $HOME_DIR/nws-publisher-go
python3 -m publishers.nws.bootstrap_nws 2>&1 | tail -20
echo ""

# NDBC bootstrap (includes buoycam)
echo "-- NDBC Bootstrap --"
cd $HOME_DIR/ndbc-publisher-go
python3 -m publishers.ndbc.bootstrap_ndbc 2>&1 | tail -20
echo ""

# CO-OPS bootstrap
echo "-- CO-OPS Bootstrap --"
cd $HOME_DIR/coops-publisher-go
python3 -m publishers.coops.bootstrap_coops 2>&1 | tail -20
echo ""

# Aviation WX bootstrap
echo "-- Aviation WX Bootstrap --"
cd $HOME_DIR/aviation-wx-publisher-go
python3 -m publishers.aviation_wx.bootstrap_aviation_wx 2>&1 | tail -20
echo ""

# USGS Water bootstrap
echo "-- USGS Water Bootstrap --"
cd $HOME_DIR/usgs-water-publisher-go
python3 -m publishers.usgs_water.bootstrap_usgs_water 2>&1 | tail -20
echo ""

# USGS NIMS bootstrap
echo "-- USGS NIMS Bootstrap --"
cd $HOME_DIR/usgs-nims-publisher-go
python3 -m publishers.usgs_nims.bootstrap_usgs_nims 2>&1 | tail -20
echo ""

# ISS bootstrap
echo "-- ISS Bootstrap --"
cd $HOME_DIR/iss-publisher-go
python3 -m publishers.iss.bootstrap_iss 2>&1 | tail -20
echo ""

echo "=== Bootstrap complete ==="

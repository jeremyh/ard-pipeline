#!/usr/bin/bash

set -eou pipefail

ARD_MODULE_VERSION={{ target_version }}
MODULE_FILES={{ target_modules_repo }}/modulefiles
MODULE_DIR={{ target_modules_repo }}/modulefiles/ard-pipeline
BASE_INSTALL_DIR={{ target_modules_repo }}/ard-pipeline

module use /g/data/v10/private/modules/modulefiles
module use /g/data/v10/public/modules/modulefiles
module use $MODULE_FILES
module use

# install module script
echo "*********************"
echo "Installing: module script"
cp module-script "$MODULE_DIR"/"$ARD_MODULE_VERSION"
chmod u-w "$MODULE_DIR"/"$ARD_MODULE_VERSION"
echo "*********************"

BASE_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[@]}")")"
BUILD_DIR="$BASE_DIR"/build
INSTALL_DIR="$BASE_INSTALL_DIR"/"$ARD_MODULE_VERSION"
CONFIG_DIR="$INSTALL_DIR"/cfg
HDF5_PLUGIN_DIR=$INSTALL_DIR/hdf5-plugins

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR" || exit 1

git clone --depth 1 https://github.com/sixy6e/idl-functions.git
git clone --depth 1 --branch {{ wagl_version }} https://github.com/GeoscienceAustralia/wagl.git
git clone --depth 1 --branch {{ eod1_version }} https://github.com/GeoscienceAustralia/eo-datasets.git eod1
git clone --depth 1 --branch {{ eod3_version }} https://github.com/GeoscienceAustralia/eo-datasets.git
git clone --depth 1 --branch {{ tesp_version }} https://github.com/OpenDataCubePipelines/tesp.git
git clone --depth 1 --branch {{ swfo_version }} https://github.com/OpenDataCubePipelines/swfo.git
git clone --depth 1 --branch {{ eugl_version }} https://github.com/OpenDataCubePipelines/eugl.git
git clone --depth 1 --branch {{ gost_version }} https://github.com/OpenDataCubePipelines/gost.git


# HDF5 and other utils
# git clone https://github.com/h5py/h5py.git
git clone --depth 1 https://github.com/Blosc/c-blosc.git
git clone --depth 1 https://github.com/Blosc/hdf5-blosc.git
git clone --depth 1 https://github.com/kiyo-masui/bitshuffle.git
# git clone --depth 1 https://github.com/LLNL/zfp
# git clone --depth 1 https://github.com/LLNL/H5Z-ZFP.git


module load ard-pipeline/"$ARD_MODULE_VERSION"

# set the pythonuserbase; allows the install to use --user rather than the complicated --install-option="--prefix=$PREFIX_PATH"
# the reason for using 'pip install . --user' instead of 'python setup.py install --prefix='
# was to avoid generating python-eggs which was causing havoc when using multiple pythonpaths
# and eggs seemed to be their own path on the pythonpath var.
# so when importing modules, it might not be the version you're expecting
export PYTHONUSERBASE="$INSTALL_DIR"

PY_BIN="$(which python)"
ENV_BASE_DIR="$(dirname "$(dirname "$PY_BIN")")"
PY_VERSION=$(python --version | cut -d" " -f2 | cut -c 1-3)
PY_SITE_PACKAGES_DIR="$INSTALL_DIR"/lib/python"$PY_VERSION"/site-packages
EASY_INSTALL_PTH="$PY_SITE_PACKAGES_DIR"/easy-install.pth
HDF5_DIR="$ENV_BASE_DIR"

# add the install path to the PYTHONPATH
export PYTHONPATH="$PYTHONPATH":"$PY_SITE_PACKAGES_DIR"

mkdir -p "$PY_SITE_PACKAGES_DIR"
mkdir -p "$HDF5_PLUGIN_DIR"
mkdir -p "$CONFIG_DIR"

echo INSTALL_DIR $INSTALL_DIR

pip install --user 'cligj==0.7.2' 'itsdangerous==2.0.1' 'nested-lookup==0.2.23' 'python-rapidjson==1.6' 'requests-cache==0.7.5' 'tenacity==6.3.1' 'url-normalize==1.4.3' 's2cloudless==1.5.0' 'Pillow==8.3.2' 'luigi==3.0.2' 'zict==2.1.0' 'setuptools==47.1.1'

EOD_PKGS=( "eod1" "eo-datasets" )
for PKG in "${EOD_PKGS[@]}"
do
  cd "$PKG" || exit 1
  echo "*********************"
  echo "Installing: $PKG"
  find -type f | xargs chmod ug+rw    # this is needed because NCI git hidden objects file permission weirdness
  pip install --user 'pystac==1.0.0rc2' .
  echo "*********************"
  cd "$BUILD_DIR" || exit 1
done

PKGS=( "idl-functions" "wagl" "eugl" "tesp" "swfo" "gost" )
for PKG in "${PKGS[@]}"
do
  cd "$PKG" || exit 1
  echo "*********************"
  echo "Installing: $PKG"
  python setup.py install --prefix="$INSTALL_DIR"
  echo "*********************"
  cd "$BUILD_DIR" || exit 1
done


# HDF5 LZF plugin
# echo "*********************"
# echo "Installing: HDF5 LZF plugin"
# cd h5py/lzf || exit 1
# gcc -O2 -fPIC -shared lzf/*.c lzf_filter.c -lhdf5 -o "$HDF5_PLUGIN_DIR"/liblzf_filter.so
# echo "*********************"
# cd "$BUILD_DIR" || exit 1


# HDF5 LZF and bitshuffle plugins
echo "*********************"
echo "Installing: HDF5 LZF and bitshuffle plugins"
cd bitshuffle || exit 1
python setup.py install --h5plugin --h5plugin-dir="$HDF5_PLUGIN_DIR" --prefix="$INSTALL_DIR"
echo "*********************"
cd "$BUILD_DIR" || exit 1


# blosc
echo "*********************"
echo "Installing: blosc"
cd c-blosc || exit 1
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" -DDEACTIVATE_SNAPPY=OFF ../
make
make install
echo "*********************"
cd "$BUILD_DIR" || exit 1


# HDF5 blosc plugin
echo "*********************"
echo "Installing: HDF5 blosc plugin"
cd hdf5-blosc || exit 1
mkdir build
cd build || exit 1
gcc -O3 -fPIC -shared ../src/blosc_plugin.c ../src/blosc_filter.c -o "$HDF5_PLUGIN_DIR"/libH5Zblosc.so -lblosc -L"$ENV_BASE_DIR"/lib -lhdf5
echo "*********************"
cd "$BUILD_DIR" || exit 1


# zfp
# echo "*********************"
# echo "Installing: zfp"
# cd zfp || exit 1
# mkdir build
# cd build || exit 1
# cmake -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" ../
# make
# make install
# echo "*********************"
# cd "$BUILD_DIR" || exit 1


# this unfortunately is not working for me, we need a -lzfp
# zfp HDF5 plugin
# echo "*********************"
# echo "Installing: zfp HDF5 plugin"
# cd H5Z-ZFP || exit 1
# make CC=gcc HDF5_HOME="$ENV_BASE_DIR" ZFP_HOME="$INSTALL_DIR" PREFIX="$INSTALL_DIR" install
# cp "$INSTALL_DIR"/plugin/libh5zzfp.so "$HDF5_PLUGIN_DIR"
# echo "*********************"
# cd "$BUILD_DIR" || exit 1


# jq
echo "*********************"
echo "Installing: jq"
wget https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 -O jq
chmod +x jq
cp jq "$INSTALL_DIR"/bin
echo "*********************"


# back to base level in this repo
cd "$BASE_DIR" || exit 1


# config files (logging and luigi)
echo "*********************"
echo "Installing: logging and luigi config files"
cp logging.cfg "$CONFIG_DIR"
cp luigi-ARD-singlefile.cfg "$CONFIG_DIR"
echo "*********************"

chmod -R u-w "$INSTALL_DIR"

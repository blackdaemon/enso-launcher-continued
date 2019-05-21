#!/bin/bash

pushd $(dirname $0) > /dev/null

source .direnv/python*/bin/activate
export PYTHONPATH=./:$PYTHONPATH

readonly COMPILED_DIR=.
readonly COMPILE_ENSO_COMMANDS=false


print_usage() {
  read -r -d '' USAGE<<EOF
Usage: $(basename $0) [options] [enso-options]

Where options can be:
  --usage:\t\tSimple usage
  --recompile\t\tForce recompilation to binary
  --recompile-full\t\tForce full recompilation
  --run-compiled\tRun compiled binary (will compile if no binary exists)

Enso-options:
EOF
  echo -e "$USAGE"
  python2 scripts/run_enso.py -h | sed "0,/^Options:/d"
}

get_enso_commands_dir() {
  # Read Enso config and obtain location of Enso commands folder
  python2 scripts/run_enso.py --get-config-var SCRIPTS_FOLDER_NAME
}

get_enso_commands() {
  # List Enso commands files
  find "$(get_enso_commands_dir)" -maxdepth 1 -name "*.py" | grep -v "_windows."
}

# Read commandline args
SKIP_ARGS=0
for arg in $@
do
  if [ "$arg" == "--usage" -o "$arg" == "--help" ]; then
    SKIP_ARGS=$(( SKIP_ARGS + 1))
    print_usage
    exit 0
  elif [ "$arg" == "--recompile" ]; then
    SKIP_ARGS=$(( SKIP_ARGS + 1))
    RECOMPILE=true
  elif [ "$arg" == "--recompile-full" ]; then
    SKIP_ARGS=$(( SKIP_ARGS + 1))
    RECOMPILE_FULL=true
  elif [ "$arg" == "--run-compiled" ]; then
    SKIP_ARGS=$(( SKIP_ARGS + 1))
    RUN_COMPILED=true
  else
    # Any other params will be appended to Enso
    break
  fi
done

# Rotate away args so that only Enso args remain
if [ $SKIP_ARGS -gt 0 ]; then
  shift $SKIP_ARGS
fi

# Is recompilation needed?
if [ "$RECOMPILE" = true -o "$RUN_COMPILED" = true -a ! -x "./enso.bin" ]; then
  if [ ! -d "$COMPILED_DIR" ]; then
    mkdir -p "$COMPILED_DIR"
  fi
  PLUGIN_INCLUDES=
  if [ "$COMPILE_ENSO_COMMANDS" = true ]; then
    for plugin in $(get_enso_commands)
    do
      PLUGIN_INCLUDES="$PLUGIN_INCLUDES --include-plugin-file=$plugin"
    done
  fi

  export NUITKA_CCACHE_BINARY=$(which ccache)
  CLANG_INSTALLED=$(type clang 2>&1 >/dev/null && echo "true")
  [ "$CLANG_INSTALLED" = true ] || echo "WARNING: Clang compiler is not installed, falling back to gcc."

  # Compile Enso
  python2 -m nuitka --show-modules --output-dir="$COMPILED_DIR" -o enso.bin \
    $([ "$CLANG_INSTALLED" = true ] && echo "--clang") \
    --lto --jobs=8 --plugin-enable=multiprocessing --python-flag="-O" \
    $([ "$RECOMPILE_FULL" = true ] && echo "--follow-imports") \
    --include-module=enso \
    --include-module=enso.contrib \
    --include-module=backports \
    --include-module=dbus \
    --include-module=pyparsing \
    --include-module=bs4 \
    --include-module=gtk \
    --include-module=Xlib \
    --include-module=gio \
    --include-module=cairo \
    --include-module=contextlib2 \
    --include-module=psutil \
    --include-module=six \
    --include-module=watchdog \
    --include-module=xdg \
    --include-plugin-file=enso/contrib/calc/exchangerates/updater.py \
    $PLUGIN_INCLUDES \
    --nofollow-import-to=enso.platform.win32 \
    --nofollow-import-to=enso.platform.osx \
    --nofollow-import-to=enso.contrib.open.platform.win32 \
    --nofollow-import-to=feedparser \
    ./scripts/run_enso.py

  if [ $? -ne 0 ]; then
    exit
  fi
  if [ ! -x "./enso.bin" ]; then
    echo "Can't find the binary enso.bin, compilation probably failed!"
    exit 1
  fi
  #mv $COMPILED_DIR/enso.bin ./enso.bin
fi

if [ "$RUN_COMPILED" = true ]; then
  pkill -f "python2.*enso"
  pkill -x "enso.bin"
  ./enso.bin $@
else
  pkill -f "python2.*enso"
  pkill -x "enso.bin"
  python2 scripts/run_enso.py $@
fi

deactivate
popd

#!/bin/bash

PRINT_HELP=false
BRANCH="refactoring"
UPDATE=true
CLEAN_VENV=true

ROOT=/home/mnguser/SubrackMngAPI 

# Function to display installer help
function display_help(){
    echo "This script will update SubrackMngAPI software in /home/mnguser/SubrackMngAPI."
    echo
    echo "Arguments:"
    echo "-b <branch> specifies branch or tag to be installed [default $BRANCH]"
    echo "-u             do not update, install locale version"
    echo "-v             do not reset venv to configured version"
    echo "-h             Print this message"
    echo ""
    }

# Process command-line arguments
while getopts "hb:uv" flag
do
    case "${flag}" in
        h) PRINT_HELP=true ;;
        b) BRANCH=${OPTARG} ;;
        u) UPDATE=false ;;
        v) CLEAN_VENV=false ;;
        \?)                                    # If expected argument omitted:
           echo "Error: missing argument."
           exit 1                   # Exit abnormally.
           ;;
    esac
done

# Check if printing help
if [ $PRINT_HELP == true ]; then
    display_help
    exit
fi

if [ $UPDATE == true ]; then
    echo "Updating API repository with online version"
    git -C $ROOT fetch || { echo 'cmd failed' ; exit 1; }
    git -C $ROOT checkout $BRANCH || { 
        echo 'cmd failed' ; 
        echo 'Available tags:' ; 
        git tag;
        echo 'Available branches:' ; 
        git branch -r;
        exit 1; }
    if [ $(git tag -l "$BRANCH") ]; then
        :
    else
        git -C $ROOT pull || { echo 'cmd failed' ; exit 1; }
    fi
    if [ $CLEAN_VENV == true ]; then
        ./deploy.sh -u -b $BRANCH || { echo 'cmd failed' ; exit 1; }
    else
        ./deploy.sh -v -u -b $BRANCH || { echo 'cmd failed' ; exit 1; }
    fi
    exit 0
fi

rm -r $ROOT/build
rm -r $ROOT/subrack_mng_api.egg-info

if [ $CLEAN_VENV == true ]; then
    echo "Reset venv to configured version"
    rm -r $ROOT/venv || { echo 'cmd failed' ; exit 1; }
    mkdir $ROOT/venv || { echo 'cmd failed' ; exit 1; }
    echo "Extract venv"
    pv $ROOT/packed-venv.tgz | tar -xz -C $ROOT/venv || { echo 'cmd failed' ; exit 1; }
    echo "Install requirements"
    pip install -r requirements.txt || { echo 'cmd failed' ; exit 1; }
    echo "Done"
    echo "Updating BIOS repository with online version"
    pip install --upgrade git+https://gitlab.com/sanitaseg/ska-low-smm-bios.git || { echo 'cmd failed' ; exit 1; }
fi

$ROOT/venv/bin/python -m pip install -U $ROOT || { echo 'cmd failed' ; exit 1; }

echo "Web server service restarting"
sudo systemctl restart web_server
echo "SubrackMngAPI updated to:"
git describe --tags --always --dirty


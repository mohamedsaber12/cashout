#!/usr/bin/env bash

updateSubmodules(){
   if [[ -z "$@" ]]; then
   echo "### HERE"
    git submodule foreach --recursive "(git checkout master; git pull)"
   else
    COMMAND="$@"
    git submodule foreach --recursive "(git checkout master; git pull; eval $COMMAND)"
   fi
}

updateSubmodules "$@"
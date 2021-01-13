#! /usr/bin/env python3

# This script regenerates TrustInSoft CI configuration.

# Run from the root of the project:
# $ python3 trustinsoft/regenerate.py

import tis

import re # sub
import json # dumps, load
import os # makedirs
from os import path # path.basename, path.isdir, path.join
import glob # iglob
from itertools import product  # Cartesian product of lists.
import shutil # copyfileobj
import argparse # ArgumentParser, add_argument, parse_args

# --------------------------------------------------------------------------- #
# ----------------------------- PARSE ARGUMENTS ----------------------------- #
# --------------------------------------------------------------------------- #

parser = argparse.ArgumentParser(
    description="Regenerate the TrustInSoft CI files.",
    epilog="Please call this script only after building jansson.")
args = parser.parse_args()

# --------------------------------------------------------------------------- #
# -------------------------------- SETTINGS --------------------------------- #
# --------------------------------------------------------------------------- #

# Directories.
common_config_path = path.join("trustinsoft", "common.config")
include_dir = path.join("trustinsoft", "include")

# Generated files which need to be a part of the repository.
files_to_copy = [
    tis.make_simple_copy_file(include_dir, "jansson_private_config.h"),
    tis.make_simple_copy_file(include_dir, path.join("src", "jansson_config.h")),
]

# Random file length.
urandom_filename = "urandom"
urandom_length = 4096

# Architectures.
machdeps = [
    {
        "machdep": "gcc_x86_32",
        "pretty_name": "little endian 32-bit (x86)",
        "fields": {
            "address-alignment": 32,
            # "compilation_cmd":
            #     tis.string_of_options(
            #         {
            #             "-D":
            #                 [
            #                     "__LITTLE_ENDIAN",
            #                     "__BYTE_ORDER=__LITTLE_ENDIAN",
            #                 ],
            #             "-U": [],
            #             "-I": [],
            #         }
            #     ),
        }
    },
    {
        "machdep": "gcc_x86_64",
        "pretty_name": "little endian 64-bit (x86)",
        "fields": {
            "address-alignment": 64,
            # "compilation_cmd":
            #     tis.string_of_options(
            #         {
            #             "-D":
            #                 [
            #                     "__LITTLE_ENDIAN",
            #                     "__BYTE_ORDER=__LITTLE_ENDIAN",
            #                 ],
            #             "-I": [],
            #         }
            #     ),
        }
    },
    {
        "machdep": "gcc_ppc_32",
        "pretty_name": "big endian 32-bit (PPC32)",
        "fields": {
            "address-alignment": 32,
            # "compilation_cmd":
            #     tis.string_of_options(
            #         {
            #             "-D":
            #                 [
            #                     "__BIG_ENDIAN",
            #                     "__BYTE_ORDER=__BIG_ENDIAN",
            #                 ],
            #              "-U": [],
            #              "-I": [],
            #         }
            #     ),
        },
    },
    {
        "machdep": "gcc_ppc_64",
        "pretty_name": "big endian 64-bit (PPC64)",
        "fields": {
            "address-alignment": 64,
            # "compilation_cmd":
            #     tis.string_of_options(
            #         {
            #             "-D":
            #                 [
            #                     "__BIG_ENDIAN",
            #                     "__BYTE_ORDER=__BIG_ENDIAN",
            #                 ],
            #             "-I": [],
            #         }
            #     ),
        },
    },
]

# --------------------------------------------------------------------------- #
# ---------------------------------- CHECKS --------------------------------- #
# --------------------------------------------------------------------------- #

# Initial check.
print("1. Check if all necessary directories and files exist...")
tis.check_dir("trustinsoft")
for file in files_to_copy:
    tis.check_file(file['src'])

# --------------------------------------------------------------------------- #
# -------------------- GENERATE trustinsoft/common.config ------------------- #
# --------------------------------------------------------------------------- #

def make_common_config():
    # C files.
    c_files_src = sorted(glob.glob(path.join("src", "*.c")))
    c_files = (
        [ "stub.c" ] +
        list(map(lambda file: path.join("..", file), c_files_src))
    )
    # Filesystem.
    suites_files = list(
        glob.glob(path.join("test", "suites", "valid", "*", "*")) +
        glob.glob(path.join("test", "suites", "invalid", "*", "*")) +
        glob.glob(path.join("test", "suites", "invalid-unicode", "*", "*")) +
        glob.glob(path.join("test", "suites", "encoding-flags", "*", "*"))
    )
    filesystem_files = (
        [
            {
                "name": path.join("/", "dev", "urandom"),
                "from": urandom_filename,
            }
        ] +
        list(map(lambda file:
            {
                "name": file,
                "from": path.join("..", file),
            },
            suites_files))
    )
    # Compilation options.
    compilation_cmd = (
        {
            "-I": [
                "..",
                path.join("..", "src"),
                "include",
                path.join("include", "src"),
            ],
            "-D": [
                "volatile=",
                "HAVE_STDINT_H",
                "HAVE_UNISTD_H",
                "NO_MASKING_TRICK",
            ],
            "-U": []
        }
    )
    # Whole common.config JSON.
    config = (
        {
            "files": c_files,
            "filesystem": { "files": filesystem_files },
            "compilation_cmd": tis.string_of_options(compilation_cmd),
            "val-clone-on-recursive-calls": True,
            "val-warn-harmless-function-pointers": False,
        }
    )
    # Done.
    return config

common_config = make_common_config()
with open(common_config_path, "w") as file:
    print("3. Generate the '%s' file." % common_config_path)
    file.write(tis.string_of_json(common_config))

# ---------------------------------------------------------------------------- #
# ------------------ GENERATE trustinsoft/<machdep>.config ------------------- #
# ---------------------------------------------------------------------------- #

def make_machdep_config(machdep):
    machdep_config = {
        "machdep": machdep["machdep"]
    }
    fields = machdep["fields"]
    for field in fields:
        machdep_config[field] = fields[field]
    return machdep_config

print("4. Generate 'trustinsoft/<machdep>.config' files...")
machdep_configs = map(make_machdep_config, machdeps)
for machdep_config in machdep_configs:
    file = path.join("trustinsoft", "%s.config" % machdep_config["machdep"])
    with open(file, "w") as f:
        print("   > Generate the '%s' file." % file)
        f.write(tis.string_of_json(machdep_config))

# --------------------------------------------------------------------------- #
# --------------------------- GENERATE tis.config --------------------------- #
# --------------------------------------------------------------------------- #

tests = sorted(glob.glob(path.join("test", "suites", "api", "test_*.c")))

other_tests = (
      glob.glob(path.join("test", "suites", "valid", "*"))
    + glob.glob(path.join("test", "suites", "invalid", "*"))
    + glob.glob(path.join("test", "suites", "invalid-unicode", "*"))
    + glob.glob(path.join("test", "suites", "encoding-flags", "*"))
)

# other_tests = [ "test/suites/valid/empty-array" ]

def make_test(test_path, machdep):
    tis_test = {
        "name": "%s, %s" % (test_path, machdep["pretty_name"]),
        "include": common_config_path,
        "include_": path.join("trustinsoft", "%s.config" % machdep["machdep"]),
        "files": [ test_path ],
    }
    return tis_test

def make_other_test(test_path, machdep):
    tis_test = {
        "name": "%s, %s" % (test_path, machdep["pretty_name"]),
        "include": common_config_path,
        "include_": path.join("trustinsoft", "%s.config" % machdep["machdep"]),
        "files": [ "test/bin/json_process.c" ],
        "val-args": (" %s" % (test_path)),
    }
    return tis_test

def make_tis_config():
    tis_tests = product(tests, machdeps)
    tis_other_tests = product(other_tests, machdeps)
    return (
        list(map(
            lambda t: make_test(t[0], t[1]),
            tis_tests
        ))
        +
        list(map(
            lambda t: make_other_test(t[0], t[1]),
            tis_other_tests
        ))
    )

tis_config = make_tis_config()
with open("tis.config", "w") as file:
    print("5. Generate the 'tis.config' file.")
    file.write(tis.string_of_json(tis_config))

# --------------------------------------------------------------------------- #
# ------------------------------ COPY .h FILES ------------------------------ #
# --------------------------------------------------------------------------- #

print("6. Copy generated files.")
for file in files_to_copy:
    with open(file['src'], 'r') as f_src:
        os.makedirs(path.dirname(file['dst']), exist_ok=True)
        with open(file['dst'], 'w') as f_dst:
            print("   > Copy '%s' to '%s'." % (file['src'], file['dst']))
            shutil.copyfileobj(f_src, f_dst)

# --------------------------------------------------------------------------- #
# ---------------------------- PREP OTHER FILES  ---------------------------- #
# --------------------------------------------------------------------------- #

print("6. Prepare other files.")
if False: # TMP
    with open(path.join("trustinsoft", urandom_filename), 'wb') as file:
        print("   > Create the 'trustinsoft/%s' file." % urandom_filename)
        file.write(os.urandom(urandom_length))


import re # sub
import json # dumps, load
from os import path # basename, isdir, join

# Outputting JSON.
def string_of_json(obj):
    # Output standard pretty-printed JSON (RFC 7159) with 4-space indentation.
    s = json.dumps(obj, indent=4)
    # Sometimes we need to have multiple "include" fields in the outputted
    # JSON, which is unfortunately impossible in the internal python
    # representation (OK, it is technically possible, but too cumbersome to
    # bother implementing it here), so we can name these fields 'include_',
    # 'include__', etc, and they are all converted to 'include' before
    # outputting as JSON.
    s = re.sub(r'"include_+"', '"include"', s)
    return s

# Make a command line from a dictionary of lists.
def string_of_options(options):
    elts = []
    for opt_prefix in options: # e.g. opt_prefix == "-D"
        for opt_value in options[opt_prefix]: # e.g. opt_value == "HAVE_OPEN"
            elts.append(opt_prefix + opt_value) # e.g. "-DHAVE_OPEN"
    return " ".join(elts)

# --------------------------------------------------------------------------- #
# ----------------------------- INITIAL CHECKS ------------------------------ #
# --------------------------------------------------------------------------- #

# Assert that a directory exists.
def check_dir(dir):
    if path.isdir(dir):
        print("   > OK! Directory '%s' exists." % dir)
    else:
        exit("   > ERROR! Directory '%s' not found." % dir)

# Assert that a file exists.
def check_file(file):
    if path.isfile(file):
        print("   > OK! File '%s' exists." % file)
    else:
        exit("   > ERROR! File '%s' not found." % file)

# --------------------------------------------------------------------------- #
# ----------------------------- GENERATED FILES ----------------------------- #
# --------------------------------------------------------------------------- #

def make_simple_copy_file(include_dir, src_path):
    return (
        {
            "src": src_path,
            "dst": path.join(include_dir, src_path),
        }
    )

# --------------------------------------------------------------------------- #
# ---------------------------- compile.commands ----------------------------- #
# --------------------------------------------------------------------------- #

def normalize_compile_command_json(compile_commands_path):
    with open(compile_commands_path, "r") as file:
        compile_commands = json.load(file)
    compile_commands.sort(key =
        lambda entry:
            entry["directory"] + " " +
            entry["file"] + " " +
            " ".join(entry["arguments"])
    )
    with open(compile_commands_path, "w") as file:
        file.write(json.dumps(compile_commands, indent=4))

def options_of_compile_command_json(compile_commands_path, options={"-D":[], "-U":[], "-I":[]}):
    D = set(options["-D"])
    U = set(options["-U"])
    I = set(options["-I"])
    with open(compile_commands_path, "r") as file:
        compile_commands = json.load(file)
        for entry in compile_commands:
            dir = path.relpath(entry["directory"])
            full_dir = path.join(
                dir,
                path.dirname(entry["file"])
            )
            for argument in entry["arguments"]:
                prefix = argument[0:2]
                value = argument[2:]
                if prefix == "-D":
                    D.add(value)
                elif prefix == "-U":
                    U.add(value)
                elif prefix == "-I":
                    I.add(path.normpath(path.join("..", dir, value)))
                    I.add(path.normpath(path.join("..", full_dir, value)))
    return {
        "-D": sorted(list(D)),
        "-I": sorted(list(I)),
        "-U": sorted(list(U)),
    }

# In case of conflicts new compile commands override old compile commands
def union_compile_commands(cc1, cc2):
    # -D
    D1 = sorted(list(set(cc1["-D"]) - set(cc2["-U"])))
    D2 = sorted(list(set(cc2["-D"]) - set(D1)))
    # -U
    U1 = sorted(list(set(cc1["-U"]) - set(cc2["-D"])))
    U2 = sorted(list(set(cc2["-U"]) - set(U1)))
    # -I
    I = sorted(list(set(cc1["-I"]) | set(cc2["-I"])))
    # All together.
    return { "-D": D1 + D2, "-U": U1 + U2, "-I": I }

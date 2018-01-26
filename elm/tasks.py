"""
Invoke tasks.py script to compile elm projects. Takes care of compiling elm to
javascript, as well as, compiling scss to css and copying any changes to html
files.
"""

# ------------------------------------------------------------------------------
# Libraries
from invoke import task
from plumbum import local, FG
from shutil import copyfile

import os
from pathlib import Path
import filecmp


# ------------------------------------------------------------------------------
# Paths
SASS_PATH = Path('C:/msys64/home/Monthy/.gem/ruby/2.1.0/bin/sass')


# ------------------------------------------------------------------------------
# Author information
__author__ = "Maarten Tegelaers"
__copyright__ = "Copyright 2018, Maarten Tegelaers"

__license__ = "All Rights Reserved"
__version__ = "0.1"
__status__ = "development"


# ------------------------------------------------------------------------------
def build_file_entry_list(root_path : str, file_type : str):
    file_entries = []
    file_dir = [root_path]
    while file_dir:
        for entry in os.scandir(file_dir.pop()):
            if not entry.name.startswith('.') and entry.is_dir():
                file_dir.append(entry.path)
            elif ( not entry.name.startswith('.')
                   and entry.name.endswith(file_type)
                   and entry.is_file()):
                file_entries.append(entry)
    return file_entries


def update_directory(path_src: Path, path_target: Path, file_type: str, verbose: bool):
    if verbose:
        print("  src:    " + str(path_src))
        print("  target: " + str(path_target))
        print("  Building file list src...", end='')

    src = build_file_entry_list(str(path_src), file_type)
    src.sort(key=(lambda x: x.path[(len(str(path_src)) +1):]))


    if verbose:
        print("[DONE]")
        print("  Building file list target...", end='')

    target = build_file_entry_list(str(path_target), file_type)
    target.sort(key=(lambda x: x.path[(len(str(path_target)) +1):]))

    if verbose:
        print("[DONE]")
        print("  Updating files:")

    # plumbum operations
    rm = local['rm']

    while src and target:
        if src[0].name == target[0].name:
            if not filecmp.cmp(src[0].path, target[0].path):
                if verbose:
                    print("    Copying:  " + src[0].path)
                copyfile(src[0].path, target[0].path)
            else:
                if verbose:
                    print("    Skipping: " + src[0].path)

            src = src[1:]
            target = target[1:]
        else:
            if ( src[0].path[(len(str(path_src)) +1):] <
                 target[0].path[(len(str(path_target)) +1):]):
                entry_path = Path(src[0].path)
                goal_path = path_target / entry_path.relative_to(path_src)

                if verbose:
                    print("    Copying:  " + str(entry_path))

                if not (goal_path.parent.exists() and
                        goal_path.parent.is_dir()):
                    goal_path.parent.mkdir()

                copyfile(str(entry_path), str(goal_path))
                src = src[1:]
            else:
                if verbose:
                    print("    Removing: " + target[0].path)
                rm(target[0].path)
                target = target[1:]

    for entry in src:
        entry_path = Path(entry.path)
        goal_path = path_target / entry_path.relative_to(path_src)

        if not (goal_path.parent.exists() and goal_path.parent.is_dir()):
            goal_path.parent.mkdir()
        if verbose:
            print("    Copying: " + str(entry_path))
        copyfile(str(entry_path), str(goal_path))

    for entry in target:
        if verbose:
            print("    Removing: " + entry.path)
        rm(entry.path)


def compile_elm(source_path : Path, target_path : Path, verbose : bool):
    pass


def compile_html(source_path : Path, target_path : Path, verbose : bool):
    if verbose:
        print("Updating html")

    update_directory(source_path, target_path, ".html", verbose)



def compile_css(source_path : Path, target_path : Path, verbose : bool):
    # -------------------------------------------------------------------------
    #  Build directory structure
    if not (target_path.exists() and target_path.is_dir()):
        target_path.mkdir(parents=True)

    # -------------------------------------------------------------------------
    #  Updating css
    if verbose:
        print("Updating css: ")

    update_directory(source_path, target_path, '.css', verbose)

    # -------------------------------------------------------------------------
    #  Compile scss files
    if verbose:
        print("Compiling scss")
    scss_src = build_file_entry_list(str(source_path), '.scss')

    ruby = local['ruby']
    sass_path = SASS_PATH

    for entry in scss_src:
        if verbose:
            print("  Compiling " + entry.path + " ... ", end="")

        entry_target_path = target_path / Path(entry.path).with_suffix(".css")

        if not (entry_target_path.parent.exists() and
                entry_target_path.parent.is_dir()):
            entry_target_path.parent.mkdir()

        #ruby(str(sass_path), entry.path, str(entry_target_path))
        print(entry.path)

        if verbose:
            print("[DONE]")


@task
def compile(ctx,
            elm=True,
            html=True
            css=True,
            verbose=False):
    source_path = Path("./src/")
    target_path = Path("./target/")

    if elm:
        compile_elm(source=( source_path / Path("elm"),
                    target=( target_path / Path("elm"),
                    verbose=verbose)
    if html:
        compile_html(source=( source_path / Path("html"),
                     target=( target_path / Path("html"),
                     verbose=verbose)
    if css:
        compile_css(source=( source_path / Path("css"),
                    target=( target_path / Path("css"),
                    verbose=verbose)

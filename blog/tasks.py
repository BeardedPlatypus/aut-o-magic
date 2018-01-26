"""
Invoke tasks.py script to update my pelican blog.
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


@task
def compile_theme(ctx, name="rubber-octopus", verbose=False):
    # Update templates
    if verbose:
        print("Updating templates")

    template_path_src = Path('.\\theme\\') / Path(name) / Path('templates')
    template_path_target = Path('.\\preview\\') / template_path_src

    if not (template_path_target.exists() and template_path_target.is_dir()):
        template_path_target.mkdir(parents=True)

    update_directory(template_path_src, template_path_target, '.html', verbose)

    # Update css
    if verbose:
        print("Updating css")

    css_path_src = Path('.\\theme\\') / Path(name) / Path('static\\css\\')
    css_path_target = Path('.\\preview\\') / css_path_src

    if not (css_path_target.exists() and css_path_target.is_dir()):
        css_path_target.mkdir(parents=True)

    update_directory(css_path_src, css_path_target, '.html', verbose)

    # Compile scss
    if verbose:
        print("Compiling scss")
    scss_src = build_file_entry_list(str(css_path_src), '.scss')

    ruby = local['ruby']
    sass_path = SASS_PATH

    for entry in scss_src:
        if verbose:
            print('  Compiling ' + entry.path + '...', end='')

        entry_target_path = Path('.\\preview\\') / Path(entry.path).with_suffix(".css")

        if not (entry_target_path.parent.exists() and
                entry_target_path.parent.is_dir()):
            entry_target_path.parent.mkdir()

        ruby(str(sass_path), entry.path, str(entry_target_path))

        if verbose:
            print("[DONE]")


@task
def update_content(ctx, verbose=False):
    if verbose:
        print("Updating content")

    content_path_src = Path('.\\content\\')
    content_path_target = Path('.\\preview\\') / content_path_src

    update_directory(content_path_src, content_path_target, '.md', verbose)


@task
def compile_preview(ctx, verbose=False, run=False):
    if verbose:
        print("Compiling preview")

    cwd = Path.cwd()
    os.chdir(str(cwd / Path("preview")))

    output = local["pelican"]()

    if verbose:
        print(output)

    os.chdir(str(cwd))

    if run:
        preview_current(ctx, verbose)


@task
def preview_current(ctx, verbose=False):
    if verbose:
        print("Running http server with current content")

    cwd = Path.cwd()
    os.chdir(str(cwd / Path("preview/output")))
    python = local["python"]

    python("-m", "http.server") & FG

    os.chdir(str(cwd))


@task
def compile_publish(ctx, verbose=False):
    if verbose:
        print("Compiling site with publish")
    cwd = Path.cwd()

    os.chdir(str(cwd / Path("preview")))

    output = local["pelican"]("-s", "publishconf.py")

    if verbose:
        print("  ", end='')
        print(output)

    os.chdir(str(cwd))

    if verbose:
        print("Copying output to production")

    path_src = cwd / Path('preview/output/')
    path_target = cwd / Path('production')

    # Content
    if verbose:
        print("  html:")

    update_directory(path_src, path_target, '.html', verbose)

    # Theme
    if verbose:
        print("  css:")
    update_directory(path_src, path_target, '.css', verbose)

    # Feeds
    if verbose:
        print("  feeds:")
    update_directory(path_src, path_target, '.xml', verbose)

#!/usr/bin/python
"""
Python application to loop over an input set of media files and copy them to
one or multiple directories with the help of a fuzzy finder.
"""

import argparse
import os
import os.path
import shutil

import mpv

from iterfzf import iterfzf

EXT_WHITELIST = set(['.bmp',
                     '.gif',
                     '.png',
                     '.jpg',
                     '.jpeg',
                     '.mkv',
                     '.webm',
                     '.mp4'])

QUIT_CHOICE = 'Quit sorting'


def parse_command_line():
    """Parses the commandline parameters and returns a named tuple of them"""
    parser = argparse.ArgumentParser()

    help_str = \
        'The source folder to scan for media files that are to sort.'
    parser.add_argument('-s', '--source', help=help_str)

    help_str = \
        'If set, scans the source folder recursively for media files.'
    parser.add_argument('-r', '--recursive', help=help_str, required=False,
                        default=False, action='store_true')

    help_str = \
        'The target folder to files get sorted to. This folder is scanned ' \
        'recursively to find each directory a source file can be copied to.'
    parser.add_argument('-t', '--target', help=help_str)

    help_str = \
        'If set, deletes a source media file after the user decides to move ' \
        'on to the next file.'
    parser.add_argument('-d', '--delete', help=help_str, required=False,
                        default=False, action='store_true')

    help_str = \
        'If set, skips to the next file after one target choice instead of ' \
        'asking until the user manually decides to move on.'
    parser.add_argument('--single', help=help_str, default=False,
                        action='store_true')

    return parser.parse_args()


def gather_files(current, recursive=False):
    """
    Scans the given directory 'current' for files with valid media extensions
    and returns the list of files as a set. If the 'recursive' flag is set,
    files from sub folders will be included.
    """
    ret = set()

    for sub in os.listdir(current):
        sub = os.path.join(current, sub)
        if recursive and os.path.isdir(sub):
            sub_files = gather_files(sub, recursive)
            ret.update(sub_files)

        if os.path.isfile(sub):
            _, ext = os.path.splitext(sub)
            if ext.lower() in EXT_WHITELIST:
                ret.add(sub)
                print('Found media file: {}'.format(sub))

    return ret


def gather_directories(current):
    """
    Scans the given current directory for is subdirectories and returns them
    as a set. This is a recursive method, also scanning subdirectories for
    their subdirectories.
    """
    ret = set()

    for sub in os.listdir(current):
        sub = os.path.join(current, sub)
        if os.path.isdir(sub):
            sub_dirs = gather_directories(sub)
            ret.update(sub_dirs)
            ret.add(sub)
            print('Found target subdirectory: {}'.format(sub))

    return ret


def sort_files(flist, dlist, delete=False, single=False):
    """
    Loops over the given file list, playing back each file in mpv whilst
    prompting the user for a target directory choice using fzf. The user is
    prompted multiple times for the same file, to copy it into multiple
    directories, until they cancel the fzf call for it to return None. Each
    prompt also includes the QUIT_CHOICE to give the user the option to abort
    sorting for now.

    If the delete flag is set, files are deleted after the user moves on to the
    next file.
    """
    total_count = len(flist)
    flist = list(flist)

    player = mpv.MPV(input_vo_keyboard=True)
    player['loop-file'] = 'inf'
    player['mute'] = True

    for fil in flist:
        player.playlist_append(fil)
    player.playlist_pos = 0

    while flist:
        cur_file = player.playlist[player.playlist_pos]['filename']
        cur_dirs = list(dlist)
        cur_dirs.append(QUIT_CHOICE)
        print('Progress: {}/{}'.format(len(flist), total_count))

        choice = True
        while cur_dirs and choice != None:
            choice = iterfzf(cur_dirs, multi=True)

            if choice:
                if QUIT_CHOICE in choice:
                    print('Quitting manually.')
                    player.quit()
                    del player
                    return

                for cho in choice:
                    shutil.copy(cur_file, cho)
                    print('Copied: {} -> {}'.format(cur_file, cho))
                    cur_dirs.remove(cho)

            if single:
                break

        player.playlist_remove()
        del flist[0]

        if delete:
            os.remove(cur_file)
            print('Removed: {}'.format(cur_file))

    player.quit()
    del player
    print('Done sorting all files.')


def main(source, target, **options):
    """
    Executes the main operation of this application: Gathering media to sort
    and prompting the user for target destinations for each file found.
    """
    if not os.path.isdir(source):
        print('Source is not a directory, aborting: {}'.format(source))
    if not os.path.isdir(target):
        print('Target is not a directory, aborting: {}'.format(target))

    recursive = options.get('recursive') or False
    delete = options.get('delete') or False
    single = options.get('single') or False

    flist = gather_files(source, recursive=recursive)
    dlist = gather_directories(target)

    if flist and dlist:
        sort_files(flist, dlist, delete=delete, single=single)
    else:
        print('Source or target directories are empty.')


if __name__ == '__main__':
    ARGS = parse_command_line()
    main(**vars(ARGS))

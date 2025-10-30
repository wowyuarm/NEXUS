#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File combiner tool
Recursively read files from a specified folder, organize them by directory structure, and concatenate them.

Ignore rules and optional parameters (please read carefully):
1) By default, the following common irrelevant directories will be ignored (both traversal and concatenation take effect):
   Note: The tests directory is now processed, if you need to ignore it, use --ignore-dir tests
   .git, .svn, .hg, __pycache__, .pytest_cache, .mypy_cache,
   logs, log, node_modules, dist, build, .next, .turbo, coverage,
   .cache, .parcel-cache, .venv

2) You can add ignore a directory (ignore by "directory name" globally, match any level):
   --ignore-dir DIRNAME
   Can be repeated multiple times, for example: --ignore-dir vendors --ignore-dir tmp

3) You can ignore a directory by "specific path" (only ignore the path and its sub-items):
   --ignore-path /abs/or/relative/path/to/dir
   Can be repeated multiple times, for example:
   python3 file_combiner.py --ignore-path ./vendors/mcp <folder_path>

4) You can ignore specific file patterns (supports wildcards):
   --ignore-file-pattern PATTERN
   Can be repeated multiple times, for example: --ignore-file-pattern "README*" --ignore-file-pattern "*.bak"

5) Smart ignore rules:
   - Automatically ignore markdown file names (without extension) that are more than 8 characters
   - Can be disabled by --no-auto-ignore-long-md

6) File tree display control:
   -t / --tree only display file tree; default does not display ignored items
   --show-ignored when combined with -t, the file tree displays and labels [ignored]

    Main usage examples:

    - Concatenate a folder: python3 file_combiner.py <folder_path>
    - Only view the file structure: python3 file_combiner.py -t <folder_path>
    - Specify output file name: python3 file_combiner.py -o output.txt <folder_path>
    - Display ignored files: python3 file_combiner.py --show-ignored <folder_path>
    - Add ignore directory name: python3 file_combiner.py --ignore-dir vendors <folder_path>
    - Ignore specific path: python3 file_combiner.py --ignore-path ./vendors/mcp <folder_path>
    - Ignore README file: python3 file_combiner.py --ignore-file-pattern "README*" <folder_path>
    - Disable automatic long markdown file name ignore: python3 file_combiner.py --no-auto-ignore-long-md <folder_path>
    """

import os
import sys
import argparse
import fnmatch
from pathlib import Path
from typing import Iterable, Set, List


def get_file_content(file_path):
    """Read file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            return f"[Cannot read file: {file_path}]"


def _default_ignore_sets():
    IGNORE_DIRS = {
        '.git', '.svn', '.hg', '__pycache__', '.pytest_cache', '.mypy_cache',
        'logs', 'log', 'node_modules', 'dist', 'build',
        '.next', '.turbo', 'coverage', '.cache', '.parcel-cache'
    }
    IGNORE_FILES = {
        '.gitignore', '.gitattributes', '.gitmodules', '.DS_Store'
    }
    IGNORE_SUFFIXES = {'.log', '.pyc', '.pyo', '.pyd'}
    return IGNORE_DIRS, IGNORE_FILES, IGNORE_SUFFIXES


def _normalize_paths(paths: Iterable[str]) -> Set[Path]:
    out: Set[Path] = set()
    for p in paths or []:
        try:
            out.add(Path(p).resolve())
        except Exception:
            continue
    return out


def _should_ignore(item: Path, root: Path, user_ignore_dirs: Set[str], user_ignore_paths: Set[Path],
                  user_ignore_patterns: List[str] = None, auto_ignore_long_md: bool = True) -> bool:
    IGNORE_DIRS, IGNORE_FILES, IGNORE_SUFFIXES = _default_ignore_sets()
    user_ignore_patterns = user_ignore_patterns or []

    # Hit user-provided specific path ignore (item is under some ignore-path)
    abs_item = item.resolve()
    for ig in user_ignore_paths:
        try:
            abs_item.relative_to(ig)
            return True
        except Exception:
            pass

    # Hit "directory name" ignore (default or user-added), any level
    all_dir_names = {p.name for p in [abs_item] + list(abs_item.parents)}
    if any(name in IGNORE_DIRS or name in user_ignore_dirs for name in all_dir_names):
        return True

    # File-level ignore
    if item.is_file():
        # Default ignored files
        if item.name in IGNORE_FILES:
            return True
        if item.suffix.lower() in IGNORE_SUFFIXES:
            return True

        # User-defined file pattern ignore
        for pattern in user_ignore_patterns:
            if fnmatch.fnmatch(item.name, pattern):
                return True

        # Auto-ignore long markdown filenames
        if auto_ignore_long_md and item.suffix.lower() == '.md':
            # Get filename without extension
            name_without_ext = item.stem
            if len(name_without_ext) > 8:
                return True

    return False


def get_file_tree(folder_path, indent="", is_last=True, show_ignored=False, user_ignore_dirs=None,
                 user_ignore_paths=None, user_ignore_patterns=None, auto_ignore_long_md=True):
    """Generate file tree structure"""
    folder_path = Path(folder_path)
    root_abs = folder_path.resolve()
    tree_lines = []

    if not folder_path.exists():
        return tree_lines

    user_ignore_dirs = set(user_ignore_dirs or [])
    user_ignore_paths = _normalize_paths(user_ignore_paths or [])
    user_ignore_patterns = user_ignore_patterns or []

    # Get all files and folders, sorted by name
    items = sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

    for i, item in enumerate(items):
        is_last_item = i == len(items) - 1

        should_ignore = _should_ignore(item, root_abs, user_ignore_dirs, user_ignore_paths,
                                     user_ignore_patterns, auto_ignore_long_md)

        if should_ignore and not show_ignored:
            continue

        # Determine connector
        if is_last:
            connector = "└── "
            next_indent = indent + "    "
        else:
            connector = "├── "
            next_indent = indent + "│   "

        # Add file/folder icons
        if item.is_file():
            suffix = item.suffix.lower()
            if suffix == '.py':
                icon = "🐍"
            elif suffix == '.md':
                icon = "📝"
            elif suffix == '.js':
                icon = "🟨"
            elif suffix == '.ts':
                icon = "🟦"
            elif suffix == '.tsx':
                icon = "🟪"
            elif suffix == '.css':
                icon = "🎨"
            elif suffix == '.html':
                icon = "🌐"
            elif suffix == '.json':
                icon = "📦"
            else:
                icon = "📄"
        else:
            icon = "📁"

        # Add ignore mark
        ignore_mark = " [ignored]" if should_ignore else ""

        tree_lines.append(f"{indent}{connector}{icon} {item.name}{ignore_mark}")

        if item.is_dir():
            # Recursively process sub-folders
            sub_tree = get_file_tree(item, next_indent, is_last_item, show_ignored, user_ignore_dirs,
                                   user_ignore_paths, user_ignore_patterns, auto_ignore_long_md)
            tree_lines.extend(sub_tree)

    return tree_lines


def combine_files_recursive(folder_path, output_file, indent="", user_ignore_dirs=None,
                          user_ignore_paths=None, user_ignore_patterns=None, auto_ignore_long_md=True):
    """Recursively read folder content and write to output file"""
    folder_path = Path(folder_path)

    if not folder_path.exists():
        print(f"Error: folder '{folder_path}' does not exist")
        return

    user_ignore_dirs = set(user_ignore_dirs or [])
    user_ignore_paths = _normalize_paths(user_ignore_paths or [])
    user_ignore_patterns = user_ignore_patterns or []

    # Get all files and folders, sorted by name
    items = sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

    for item in items:
        # Unified ignore judgment
        if _should_ignore(item, folder_path.resolve(), user_ignore_dirs, user_ignore_paths,
                         user_ignore_patterns, auto_ignore_long_md):
            if item.is_dir():
                print(f"Ignoring folder: {item} [ignored]")
            else:
                print(f"Ignoring file: {item} [ignored]")
            continue

        if item.is_file():
            # Only process common code and documentation files
            if item.suffix.lower() in ['.py', '.md', '.js', '.ts', '.tsx', '.css', '.html', '.json']:
                print(f"Processing file: {item}")

                # Write file name separator
                separator = "=" * 80
                output_file.write(f"\n{indent}{separator}\n")
                output_file.write(f"{indent}文件名: {item.name}\n")
                output_file.write(f"{indent}路径: {item.relative_to(folder_path)}\n")
                output_file.write(f"{indent}{separator}\n\n")

                # Read and write file content
                content = get_file_content(item)
                output_file.write(f"{indent}{content}\n")

        elif item.is_dir():
            # Recursively process sub-folders
            print(f"Entering folder: {item}")

            # Write folder separator
            folder_separator = "-" * 60
            output_file.write(f"\n{indent}{folder_separator}\n")
            output_file.write(f"{indent}Folder: {item.name}\n")
            output_file.write(f"{indent}{folder_separator}\n\n")

            # Recursively process sub-folder content
            combine_files_recursive(item, output_file, indent + "  ", user_ignore_dirs,
                                   user_ignore_paths, user_ignore_patterns, auto_ignore_long_md)


def main():
    parser = argparse.ArgumentParser(description='Recursively read folder and concatenate Python files')
    parser.add_argument('folder_path', help='Path to the folder to read')
    parser.add_argument('-o', '--output', help='Output file name (optional, default uses folder name)')
    parser.add_argument('-t', '--tree', action='store_true', help='Display file structure tree')
    parser.add_argument('--show-ignored', action='store_true', help='Display ignored files in file tree')
    parser.add_argument('--ignore-dir', action='append', default=[], help='Ignore by directory name (can be repeated)')
    parser.add_argument('--ignore-path', action='append', default=[], help='Ignore by specific path (can be repeated)')
    parser.add_argument('--ignore-file-pattern', action='append', default=[],
                       help='Ignore by file name pattern (supports wildcards, can be repeated), for example: README*')
    parser.add_argument('--no-auto-ignore-long-md', action='store_true',
                       help='Disable automatic long markdown file name ignore')

    args = parser.parse_args()

    # Convert relative path to absolute path
    folder_path = Path(args.folder_path).resolve()

    if not folder_path.exists():
        print(f"Error: folder '{folder_path}' does not exist")
        sys.exit(1)

    # Normalize user ignore configuration
    user_ignore_dirs = set(args.ignore_dir or [])
    user_ignore_paths = _normalize_paths(args.ignore_path or [])
    user_ignore_patterns = args.ignore_file_pattern or []
    auto_ignore_long_md = not args.no_auto_ignore_long_md

    # Save current working directory
    original_cwd = Path.cwd()

    # If only displaying file tree
    if args.tree:
        print(f"📁 File structure: {folder_path}")
        print("=" * 60)
        tree_lines = get_file_tree(folder_path, show_ignored=args.show_ignored,
                                 user_ignore_dirs=user_ignore_dirs, user_ignore_paths=user_ignore_paths,
                                 user_ignore_patterns=user_ignore_patterns, auto_ignore_long_md=auto_ignore_long_md)
        for line in tree_lines:
            print(line)
        return

    try:
        # Switch to parent directory of target folder
        os.chdir(folder_path.parent)

        # Determine output file name
        if args.output:
            # Ensure output file has .txt extension
            output_filename = args.output
            if not output_filename.endswith('.txt'):
                output_filename += '.txt'
        else:
            output_filename = f"{folder_path.name}_combined.txt"

        # Ensure output file path is relative to original working directory
        output_path = original_cwd / output_filename

        print(f"Starting to process folder: {folder_path}")
        print(f"Output file: {output_path}")

        # Display file structure (if enabled)
        if args.show_ignored:
            print("\n📁 File structure (includes ignored files):")
            print("-" * 40)
            tree_lines = get_file_tree(folder_path, show_ignored=True, user_ignore_dirs=user_ignore_dirs,
                                     user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                     auto_ignore_long_md=auto_ignore_long_md)
            for line in tree_lines:
                print(line)
            print("-" * 40)

        # Create output file
        with open(output_path, 'w', encoding='utf-8') as output_file:
            # Write file header
            output_file.write(f"File concatenation result\n")
            output_file.write(f"Source folder: {folder_path.absolute()}\n")
            output_file.write(f"Generated time: {Path().cwd()}\n")
            output_file.write("=" * 80 + "\n\n")

            # Write file structure
            output_file.write("📁 File structure:\n")
            output_file.write("-" * 40 + "\n")
            tree_lines = get_file_tree(folder_path, show_ignored=False, user_ignore_dirs=user_ignore_dirs,
                                     user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                     auto_ignore_long_md=auto_ignore_long_md)
            for line in tree_lines:
                output_file.write(line + "\n")
            output_file.write("-" * 40 + "\n\n")

            # Start recursive processing
            combine_files_recursive(folder_path, output_file, user_ignore_dirs=user_ignore_dirs,
                                   user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                   auto_ignore_long_md=auto_ignore_long_md)

            # Write file footer
            output_file.write("\n" + "=" * 80 + "\n")
            output_file.write("File concatenation completed\n")

        print(f"Processing completed! Output file: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()

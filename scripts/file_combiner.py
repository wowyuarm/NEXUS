#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件拼接工具
递归读取指定文件夹中的文件，按目录结构组织并拼接

忽略规则与可选参数说明（请务必阅读）:
1) 默认会忽略以下常见无关目录（遍历与拼接均生效）：
   .git, .svn, .hg, __pycache__, .pytest_cache, .mypy_cache,
   test, tests, logs, log, node_modules, dist, build, .next, .turbo, coverage,
   .cache, .parcel-cache

   默认会忽略以下常见无关文件与扩展名：
   .gitignore, .gitattributes, .gitmodules, .DS_Store，以及后缀：.log, .pyc, .pyo, .pyd

2) 你可以追加忽略某个目录（按“目录名”全局忽略，任意层级匹配）：
   --ignore-dir DIRNAME
   可重复多次，例如：--ignore-dir vendors --ignore-dir tmp

3) 你可以忽略某个“具体路径”的目录（仅忽略该路径及其子项）：
   --ignore-path /abs/or/relative/path/to/dir
   可重复多次，例如：
   python3 file_combiner.py --ignore-path ./vendors/mcp <folder_path>

4) 你可以忽略特定文件模式（支持通配符）：
   --ignore-file-pattern PATTERN
   可重复多次，例如：--ignore-file-pattern "README*" --ignore-file-pattern "*.bak"

5) 智能忽略规则：
   - 自动忽略markdown文件名（不含扩展名）超过8个字符的文件
   - 可通过 --no-auto-ignore-long-md 禁用此功能

6) 文件树显示控制：
   -t / --tree 只显示文件树；默认不显示被忽略项
   --show-ignored 与 -t 配合时，文件树中显示并标注 [忽略]

主要用法示例：

- 拼接某个文件夹：python3 file_combiner.py <folder_path>
- 只查看文件结构：python3 file_combiner.py -t <folder_path>
- 指定输出文件名：python3 file_combiner.py -o output.txt <folder_path>
- 显示被忽略的文件：python3 file_combiner.py --show-ignored <folder_path>
- 追加忽略目录名：python3 file_combiner.py --ignore-dir vendors <folder_path>
- 忽略具体路径：python3 file_combiner.py --ignore-path ./vendors/mcp <folder_path>
- 忽略README文件：python3 file_combiner.py --ignore-file-pattern "README*" <folder_path>
- 禁用长markdown文件名自动忽略：python3 file_combiner.py --no-auto-ignore-long-md <folder_path>
"""

import os
import sys
import argparse
import fnmatch
from pathlib import Path
from typing import Iterable, Set, List


def get_file_content(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            return f"[无法读取文件: {file_path}]"


def _default_ignore_sets():
    IGNORE_DIRS = {
        '.git', '.svn', '.hg', '__pycache__', '.pytest_cache', '.mypy_cache',
        'test', 'tests', 'logs', 'log', 'node_modules', 'dist', 'build',
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

    # 命中用户提供的“具体路径”忽略（item 位于某 ignore-path 下）
    abs_item = item.resolve()
    for ig in user_ignore_paths:
        try:
            abs_item.relative_to(ig)
            return True
        except Exception:
            pass

    # 命中“目录名”忽略（默认或用户追加），任意层级
    all_dir_names = {p.name for p in [abs_item] + list(abs_item.parents)}
    if any(name in IGNORE_DIRS or name in user_ignore_dirs for name in all_dir_names):
        return True

    # 文件级别忽略
    if item.is_file():
        # 默认忽略文件
        if item.name in IGNORE_FILES:
            return True
        if item.suffix.lower() in IGNORE_SUFFIXES:
            return True

        # 用户自定义文件模式忽略
        for pattern in user_ignore_patterns:
            if fnmatch.fnmatch(item.name, pattern):
                return True

        # 自动忽略长markdown文件名
        if auto_ignore_long_md and item.suffix.lower() == '.md':
            # 获取不含扩展名的文件名
            name_without_ext = item.stem
            if len(name_without_ext) > 8:
                return True

    return False


def get_file_tree(folder_path, indent="", is_last=True, show_ignored=False, user_ignore_dirs=None,
                 user_ignore_paths=None, user_ignore_patterns=None, auto_ignore_long_md=True):
    """生成文件树结构"""
    folder_path = Path(folder_path)
    root_abs = folder_path.resolve()
    tree_lines = []

    if not folder_path.exists():
        return tree_lines

    user_ignore_dirs = set(user_ignore_dirs or [])
    user_ignore_paths = _normalize_paths(user_ignore_paths or [])
    user_ignore_patterns = user_ignore_patterns or []

    # 获取所有文件和文件夹，按名称排序
    items = sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

    for i, item in enumerate(items):
        is_last_item = i == len(items) - 1

        should_ignore = _should_ignore(item, root_abs, user_ignore_dirs, user_ignore_paths,
                                     user_ignore_patterns, auto_ignore_long_md)

        if should_ignore and not show_ignored:
            continue

        # 确定连接符
        if is_last:
            connector = "└── "
            next_indent = indent + "    "
        else:
            connector = "├── "
            next_indent = indent + "│   "

        # 添加文件/文件夹图标
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

        # 添加忽略标记
        ignore_mark = " [忽略]" if should_ignore else ""

        tree_lines.append(f"{indent}{connector}{icon} {item.name}{ignore_mark}")

        if item.is_dir():
            # 递归处理子文件夹
            sub_tree = get_file_tree(item, next_indent, is_last_item, show_ignored, user_ignore_dirs,
                                   user_ignore_paths, user_ignore_patterns, auto_ignore_long_md)
            tree_lines.extend(sub_tree)

    return tree_lines


def combine_files_recursive(folder_path, output_file, indent="", user_ignore_dirs=None,
                          user_ignore_paths=None, user_ignore_patterns=None, auto_ignore_long_md=True):
    """递归读取文件夹内容并写入输出文件"""
    folder_path = Path(folder_path)

    if not folder_path.exists():
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return

    user_ignore_dirs = set(user_ignore_dirs or [])
    user_ignore_paths = _normalize_paths(user_ignore_paths or [])
    user_ignore_patterns = user_ignore_patterns or []

    # 获取所有文件和文件夹，按名称排序
    items = sorted(folder_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

    for item in items:
        # 统一忽略判断
        if _should_ignore(item, folder_path.resolve(), user_ignore_dirs, user_ignore_paths,
                         user_ignore_patterns, auto_ignore_long_md):
            if item.is_dir():
                print(f"忽略文件夹: {item}")
            else:
                print(f"忽略文件: {item}")
            continue

        if item.is_file():
            # 只处理常见代码和文档文件
            if item.suffix.lower() in ['.py', '.md', '.js', '.ts', '.tsx', '.css', '.html', '.json']:
                print(f"处理文件: {item}")

                # 写入文件名分隔线
                separator = "=" * 80
                output_file.write(f"\n{indent}{separator}\n")
                output_file.write(f"{indent}文件名: {item.name}\n")
                output_file.write(f"{indent}路径: {item.relative_to(folder_path)}\n")
                output_file.write(f"{indent}{separator}\n\n")

                # 读取并写入文件内容
                content = get_file_content(item)
                output_file.write(f"{indent}{content}\n")

        elif item.is_dir():
            # 递归处理子文件夹
            print(f"进入文件夹: {item}")

            # 写入文件夹分隔线
            folder_separator = "-" * 60
            output_file.write(f"\n{indent}{folder_separator}\n")
            output_file.write(f"{indent}文件夹: {item.name}\n")
            output_file.write(f"{indent}{folder_separator}\n\n")

            # 递归处理子文件夹内容
            combine_files_recursive(item, output_file, indent + "  ", user_ignore_dirs,
                                   user_ignore_paths, user_ignore_patterns, auto_ignore_long_md)


def main():
    parser = argparse.ArgumentParser(description='递归读取文件夹并拼接Python文件')
    parser.add_argument('folder_path', help='要读取的文件夹路径')
    parser.add_argument('-o', '--output', help='输出文件名（可选，默认使用文件夹名）')
    parser.add_argument('-t', '--tree', action='store_true', help='显示文件结构树')
    parser.add_argument('--show-ignored', action='store_true', help='在文件树中显示被忽略的文件')
    parser.add_argument('--ignore-dir', action='append', default=[], help='按目录名忽略（可重复）')
    parser.add_argument('--ignore-path', action='append', default=[], help='按具体路径忽略（可重复）')
    parser.add_argument('--ignore-file-pattern', action='append', default=[],
                       help='按文件名模式忽略（支持通配符，可重复），例如：README*')
    parser.add_argument('--no-auto-ignore-long-md', action='store_true',
                       help='禁用自动忽略长markdown文件名的功能')

    args = parser.parse_args()

    # 将相对路径转换为绝对路径
    folder_path = Path(args.folder_path).resolve()

    if not folder_path.exists():
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        sys.exit(1)

    # 归一化用户忽略配置
    user_ignore_dirs = set(args.ignore_dir or [])
    user_ignore_paths = _normalize_paths(args.ignore_path or [])
    user_ignore_patterns = args.ignore_file_pattern or []
    auto_ignore_long_md = not args.no_auto_ignore_long_md

    # 保存当前工作目录
    original_cwd = Path.cwd()

    # 如果只显示文件树
    if args.tree:
        print(f"📁 文件结构: {folder_path}")
        print("=" * 60)
        tree_lines = get_file_tree(folder_path, show_ignored=args.show_ignored,
                                 user_ignore_dirs=user_ignore_dirs, user_ignore_paths=user_ignore_paths,
                                 user_ignore_patterns=user_ignore_patterns, auto_ignore_long_md=auto_ignore_long_md)
        for line in tree_lines:
            print(line)
        return

    try:
        # 切换到目标文件夹的父目录
        os.chdir(folder_path.parent)

        # 确定输出文件名
        if args.output:
            # 确保输出文件有 .txt 扩展名
            output_filename = args.output
            if not output_filename.endswith('.txt'):
                output_filename += '.txt'
        else:
            output_filename = f"{folder_path.name}_combined.txt"

        # 确保输出文件的路径是相对于原始工作目录的
        output_path = original_cwd / output_filename

        print(f"开始处理文件夹: {folder_path}")
        print(f"输出文件: {output_path}")

        # 显示文件结构（如果启用）
        if args.show_ignored:
            print("\n📁 文件结构（包含忽略文件）:")
            print("-" * 40)
            tree_lines = get_file_tree(folder_path, show_ignored=True, user_ignore_dirs=user_ignore_dirs,
                                     user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                     auto_ignore_long_md=auto_ignore_long_md)
            for line in tree_lines:
                print(line)
            print("-" * 40)

        # 创建输出文件
        with open(output_path, 'w', encoding='utf-8') as output_file:
            # 写入文件头
            output_file.write(f"文件拼接结果\n")
            output_file.write(f"源文件夹: {folder_path.absolute()}\n")
            output_file.write(f"生成时间: {Path().cwd()}\n")
            output_file.write("=" * 80 + "\n\n")

            # 写入文件结构
            output_file.write("📁 文件结构:\n")
            output_file.write("-" * 40 + "\n")
            tree_lines = get_file_tree(folder_path, show_ignored=False, user_ignore_dirs=user_ignore_dirs,
                                     user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                     auto_ignore_long_md=auto_ignore_long_md)
            for line in tree_lines:
                output_file.write(line + "\n")
            output_file.write("-" * 40 + "\n\n")

            # 开始递归处理
            combine_files_recursive(folder_path, output_file, user_ignore_dirs=user_ignore_dirs,
                                   user_ignore_paths=user_ignore_paths, user_ignore_patterns=user_ignore_patterns,
                                   auto_ignore_long_md=auto_ignore_long_md)

            # 写入文件尾
            output_file.write("\n" + "=" * 80 + "\n")
            output_file.write("文件拼接完成\n")

        print(f"处理完成！输出文件: {output_path}")

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()

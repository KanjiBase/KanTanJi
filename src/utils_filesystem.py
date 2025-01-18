import os
import shutil


def delete_filesystem_node(node):
    if os.path.exists(node):
        if os.path.isdir(node):
            shutil.rmtree(node)
        else:
            os.remove(node)


def merge_trees(source, target):
    """
    Merge the directory tree of `source` into `target`. Files in `source` replace those in `target`.
    """
    if not os.path.exists(source):
        raise ValueError(f"Source directory '{source}' does not exist.")

    if not os.path.exists(target):
        os.makedirs(target)

    for root, dirs, files in os.walk(source):
        relative_path = os.path.relpath(root, source)
        target_root = os.path.join(target, relative_path)
        os.makedirs(target_root, exist_ok=True)

        # Replace files in the target
        for file_name in files:
            source_file = os.path.join(root, file_name)
            target_file = os.path.join(target_root, file_name)
            shutil.copy2(source_file, target_file)  # Replace file in target

        for dir_name in dirs:
            target_subdir = os.path.join(target_root, dir_name)
            os.makedirs(target_subdir, exist_ok=True)


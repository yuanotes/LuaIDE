import hashlib
import sublime
import os

def push_value(obj, key, value):
    """
    Set obj[key] to an array, and push value to it.
    """
    if key in obj and isinstance(obj[key], list):
        obj[key].append(value)
    else:
        obj[key] = [value]


def push_function(obj, func_name, func_parents, func_arguments, func_loc):
    func_loc.update({
        "parents": func_parents,
        "args": func_arguments,
    })
    push_value(obj, func_name, func_loc)


def get_location(filename, loc):
    """
    loc = {
        start: {
            line: <num>,
            column: <num>,
        },
        end: {
            line: <num>,
            column: <num>
        }
    }
    """
    return {"path": filename,
            "loc": {
                "row": loc["start"]["line"],
                "col": loc["start"]["column"],
            }}

def get_file_md5(filepath):
    return str(hashlib.md5(open(filepath, 'rb').read()).hexdigest())

def get_tmp_path():
    path = os.path.join(sublime.packages_path(), "User", "LuaIDE.cache")
    if not os.path.exists(path):
        os.mkdir(path)
    return path

def get_cache_file_path(src_file_path):
    src_md5 = get_file_md5(src_file_path)
    src_file_name = os.path.basename(src_file_path)
    return os.path.join(get_tmp_path(), src_md5 + "_" + src_file_name)

def open_cache_file(src_file_path):
    cache_file_path = get_cache_file_path(src_file_path)
    if os.path.exists(cache_file_path):
        return open(cache_file_path, 'r').read()
    return ""

def save_cache_file(src_file_path, file_content):
    cache_file_path = get_cache_file_path(src_file_path)
    with open(cache_file_path, "w") as ofile:
        ofile.write(file_content)
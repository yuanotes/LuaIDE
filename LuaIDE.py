import sublime, sublime_plugin
import os
import subprocess
from subprocess import Popen, PIPE
import json
from json.decoder import WHITESPACE

try:
    import utils.walk
except:
    from .utils import walk

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
LUAPARSER_PATH = os.path.join(CUR_DIR, "lib/node_modules/luaparse/bin/luaparse")


settings = None
class Settings:

    def __init__(self):
        package_settings = sublime.load_settings("LuaIDE.sublime-settings")
        package_settings.add_on_change("node_bin_path", settings_changed)

        self.node_bin_path = package_settings.get("node_bin_path", "node")
        self.package_settings = package_settings

    def unload(self):
        self.package_settings.clear_on_change("node_bin_path")


def plugin_loaded():
    global settings
    settings = Settings()


def plugin_unloaded():
    global settings
    if settings != None:
        settings.unload()
        settings = None

def settings_changed():
    global settings
    if settings != None:
        settings.unload()
        settings = None
    settings = Settings()

def iterload(string, cls=json.JSONDecoder, **kwargs):
    string = str(string)
    decoder = cls(**kwargs)
    idx = WHITESPACE.match(string, 0).end()
    while idx < len(string):
        obj, end = decoder.raw_decode(string, idx)
        yield obj
        idx = WHITESPACE.match(string, end).end()

def get_raw_ast(lua_src_file):
    cmd_list = [settings.node_bin_path, LUAPARSER_PATH, "--no-comments", "--locations", lua_src_file]
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = Popen(cmd_list, stdout=PIPE, startupinfo=startupinfo)
    (output, err) = process.communicate()
    exit_code = process.wait()

    if exit_code == 0:
        return str(output, encoding="utf-8")
    else:
        return None


def get_project_path():
    window = sublime.active_window()
    if window:
        folders = window.folders()
        if folders:
            return folders[0]
    return None

def parse_all_lua_files():
    project_path = get_project_path()
    for root, dirs, files in os.walk(project_path):
        for src_file in files:
            if src_file.endswith(".lua"):
                src_file = os.path.join(root, src_file)
                if os.path.exists(src_file):
                    parse(src_file)

def parse(lua_src_file):
    if lua_src_file in walk.FILE_RELATED:
        return

    raw = get_raw_ast(lua_src_file)
    if raw:
        for ast_obj in iterload(raw):
            walk.iterate_ast(lua_src_file, ast_obj)
    else:
        print("Get AST from lua files error.")

class LuaReloadCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        parse_all_lua_files()
        print("VARIABLES:", walk.VARIABLES)
        print("FUNCTIONS:", walk.FUNCTIONS)
        print("FILES:", walk.FILE_RELATED)

class LuaAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.match_selector(locations[0], "source.lua"):
            results = []
            prefix_u = prefix.upper()
            for key, arr in walk.VARIABLES.items():
                if key.upper().startswith(prefix_u):
                    for value in arr:
                        result = "{0}\t{1}(Variable)".format(key, os.path.basename(value["path"])), key
                        results.append(result)
            for key, arr in walk.FUNCTIONS.items():
                if key.upper().startswith(prefix_u):
                    for value in arr:
                        result = "{0}\t{1}(Function)".format(key, os.path.basename(value["path"])), key
                        results.append(result)
            if len(results) > 0:
                # return list(set(results))
                return (list(set(results)), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
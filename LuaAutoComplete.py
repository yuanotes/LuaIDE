import sublime, sublime_plugin
import os
import subprocess
from subprocess import Popen, PIPE
import json
from json.decoder import WHITESPACE


CUR_DIR = os.path.dirname(os.path.abspath(__file__))
LUAPARSER_PATH = os.path.join(CUR_DIR, "lib/node_modules/luaparse/bin/luaparse")

VARIABLES = {}
FUNCTIONS = {}

FILE_RELATED = {}

settings = None


class Settings:

    def __init__(self):
        package_settings = sublime.load_settings("LuaAutoComplete.sublime-settings")
        package_settings.add_on_change("node_bin_path", settings_changed)
        package_settings.add_on_change("lua_package_paths", settings_changed)

        self.node_bin_path = package_settings.get("node_bin_path", "node")
        self.lua_package_paths = package_settings.get("lua_package_paths", [])
        self.package_settings = package_settings

    def unload(self):
        self.package_settings.clear_on_change("node_bin_path")
        self.package_settings.clear_on_change("lua_package_paths")


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

def push_value(obj, key, value):
    if key in obj and isinstance(obj[key], list):
        obj[key].append(value)
    else:
        obj[key] = [value]


def parse_assignment_statement(filename, ast_obj):
    if ast_obj["type"] == "AssignmentStatement":
        for v in ast_obj["variables"]:
            if v["type"] == "Identifier":
                global VARIABLES
                push_value( VARIABLES, v["name"], get_location(filename, v["loc"]))
                global FILE_RELATED
                push_value( FILE_RELATED, filename, v["name"])


def iterate_ast(filename, ast_obj):
    if ast_obj["type"] in ["Chunk"]:
        for b in ast_obj["body"]:
            iterate_ast(filename, b)
    else:
        parse_assignment_statement(filename, ast_obj)

def parse(lua_src_file):
    raw = get_raw_ast(lua_src_file)
    for ast_obj in iterload(raw):
        iterate_ast(lua_src_file, ast_obj)

class LuaReloadCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_start = self.view.settings().get("lua_entry_file", self.view.file_name())
        print("Reload ", file_start)
        if file_start and file_start.endswith(".lua"):
            parse(file_start)

class LuaAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.match_selector(locations[0], "source.lua"):
            results = []
            for key in VARIABLES.keys():
                if key.startswith(prefix):
                    results.append(key)
            if len(results) > 0:
                # return list(set(results))
                return (list(set(results)),
                        sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
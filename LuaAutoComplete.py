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

def get_project_path():
    window = sublime.active_window()
    if window:
        folders = window.folders()
        if folders:
            return folders[0]
    return None


def parse_assignment_statement(filename, ast_obj):
    if ast_obj["type"] == "AssignmentStatement":
        for v in ast_obj["variables"]:
            if v["type"] == "Identifier":
                global VARIABLES
                push_value( VARIABLES, v["name"], get_location(filename, v["loc"]))
                global FILE_RELATED
                push_value( FILE_RELATED, filename, v["name"])

def parse_require_statement(filename, ast_obj):
    if ast_obj["type"] == "CallExpression" and \
        ast_obj["base"]["type"] == "Identifier" and \
        ast_obj["base"]["name"] == "require":
        if ast_obj["arguments"] and \
            ast_obj["arguments"][0]["type"] == "StringLiteral":

            required_module = ast_obj["arguments"][0]["value"]
            required_module = required_module.replace(r".", "/") + ".lua"

            project_path = get_project_path()

            if project_path:
                global settings
                for module_path in settings.lua_package_paths:
                    module_path = os.path.join(project_path, module_path, required_module)
                    if os.path.exists(module_path):
                        parse(module_path)
                        return;


def iterate_ast(filename, ast_obj):
    if ast_obj["type"] in ["Chunk"]:
        for b in ast_obj["body"]:
            iterate_ast(filename, b)
    elif ast_obj["type"] == "AssignmentStatement":
        parse_assignment_statement(filename, ast_obj)
        for c in ast_obj["init"]:
            iterate_ast(filename, c)
    elif ast_obj["type"] == "CallExpression":
        iterate_ast(filename, ast_obj["base"])
        parse_require_statement(filename, ast_obj)
    elif ast_obj["type"] == "CallStatement":
        iterate_ast(filename, ast_obj["expression"])
    elif ast_obj["type"] == "MemberExpression":
        iterate_ast(filename, ast_obj["base"])

def parse(lua_src_file):
    global FILE_RELATED
    if lua_src_file in FILE_RELATED:
        return

    raw = get_raw_ast(lua_src_file)
    if raw:
        for ast_obj in iterload(raw):
            iterate_ast(lua_src_file, ast_obj)
    else:
        print("Get AST from lua files error.")

class LuaReloadCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        project_lua_package_paths = self.view.settings().get("lua_package_paths")
        if project_lua_package_paths and isinstance(project_lua_package_paths, list):
            global settings
            settings.lua_package_paths.extend(project_lua_package_paths)

        file_start = self.view.settings().get("lua_entry_file", None)
        if not file_start:
            print("Please set `lua_entry_file` to reload lua.")
            return

        file_start_path = ""
        if file_start.startswith("/"):
            file_start_path = file_start
        else:
            project_path = get_project_path()
            if project_path:
                file_start_path = os.path.join(project_path, file_start)

        if os.path.exists(file_start_path) and file_start_path.endswith(".lua"):
            global VARIABLES
            global FUNCTIONS
            global FILE_RELATED
            VARIABLES = {}
            FUNCTIONS = {}
            FILE_RELATED = {}
            print("Reload: ", file_start_path)
            parse(file_start_path)

        print("VARIABLES:", VARIABLES.keys())
        print("FUNCTIONS:", FUNCTIONS)
        print("FILES:", FILE_RELATED.keys())

class LuaAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.match_selector(locations[0], "source.lua"):
            results = []
            global VARIABLES
            for key in VARIABLES.keys():
                if key.upper().startswith(prefix.upper()):
                    results.append(key)
            if len(results) > 0:
                # return list(set(results))
                return (list(set(results)), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
import os
import json
import re
import subprocess
import functools
from subprocess import Popen, PIPE
from json.decoder import WHITESPACE


import sublime, sublime_plugin


try:
    import utils.walk
    import utils.helper
except:
    from .utils import walk
    from .utils import helper

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
    cached_content = helper.open_cache_file(lua_src_file)
    if cached_content:
        return cached_content

    cmd_list = [settings.node_bin_path, LUAPARSER_PATH, "--no-comments", "--locations", lua_src_file]
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    process = Popen(cmd_list, stdout=PIPE, startupinfo=startupinfo)
    (output, err) = process.communicate()
    exit_code = process.wait()

    if exit_code == 0:
        result_str = str(output, encoding="utf-8")
        helper.save_cache_file(lua_src_file, result_str)
        return result_str
    else:
        return None


def get_project_path_list():
    window = sublime.active_window()
    if window:
        folders = window.folders()
        if folders:
            return folders
    return []


def parse_all_lua_files():
    try:
        view = sublime.active_window().active_view()
    except:
        view = None
        return

    lua_src_folders = view.settings().get("lua_src_folders", [])
    if not lua_src_folders:
        print("Please set `lua_src_folders` in settings file.")
        sublime.status_message("Please set `lua_src_folders` in settings file.")
        return
    if not isinstance(lua_src_folders, list):
        print("Please set `lua_src_folders` as an array.")
        sublime.status_message("Please set `lua_src_folders` as an array.")
        return

    project_list = get_project_path_list()
    project_count = len(project_list)
    lua_src_count = len(lua_src_folders)
    lua_src_absolute_paths = []
    for i in range(len(lua_src_folders)):
        lua_src = lua_src_folders[i]

        if lua_src.startswith("/"):
            if os.path.exists(lua_src):
                lua_src_absolute_paths.append(lua_src)
            continue

        if i > (project_count - 1):
            continue
        else:
            project_path = project_list[i]
            lua_src_abspath = os.path.join(project_path, lua_src)
            if os.path.exists(lua_src_abspath):
                lua_src_absolute_paths.append(lua_src_abspath)

    exclude_patterns = [".git", ".svn"]
    walk.VARIABLES = {}
    walk.FUNCTIONS = {}
    walk.FILE_RELATED = {}
    for src_path in lua_src_absolute_paths:
        for root, dirs, files in os.walk(src_path):
            # ignore exclude_patterns
            to_continue = False
            for pattern in exclude_patterns:
                if re.search(root, pattern):
                    to_continue = True
                    break
            if to_continue:
                continue
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
        # print("VARIABLES:", walk.VARIABLES)
        # print("FUNCTIONS:", walk.FUNCTIONS)
        # print("FILES:", walk.FILE_RELATED)

class LuaAutocomplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.match_selector(locations[0], "source.lua"):
            results = []
            prefix_u = prefix.upper()
            for key, arr in walk.VARIABLES.items():
                if key.upper().startswith(prefix_u):
                    for value in arr:
                        result = "{0}\t{1}".format(key, os.path.basename(value["path"])), key
                        results.append(result)
            for key, arr in walk.FUNCTIONS.items():
                if key.upper().startswith(prefix_u):
                    for value in arr:
                        args_str = "({0})".format(", ".join(value["args"]))
                        result = "{0}{1}\t{2}".format(key, args_str,  os.path.basename(value["path"])), key
                        results.append(result)
            if len(results) > 0:
                # return list(set(results))
                return (list(set(results)), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

class LuaGotoDefinitionCommand(sublime_plugin.TextCommand):    
    def run(self, edit):
        # select text
        sel=self.view.substr(self.view.sel()[0])
        if len(sel)==0:
            # extend to the `word` under cursor
            sel=self.view.substr(self.view.word(self.view.sel()[0]))
        # find all match file
        matchList=[]
        showList=[]
        for key, arr in walk.VARIABLES.items():
            if key == sel:
                for value in arr:
                    matchList.append(value)
                    showList.append("{0} - {1}".format(key, os.path.basename(value["path"])))
        for key, arr in walk.FUNCTIONS.items():
            if key == sel:
                for value in arr:
                    matchList.append(value)
                    args_str = "({0})".format(", ".join(value["args"]))
                    showList.append("{0}{1} - {2}".format(key, args_str, os.path.basename(value["path"])))
        if len(matchList) == 0:
            sublime.status_message("Can not find definition '%s'"%(sel))
        elif len(matchList) == 1:
            self.gotoDefinition(matchList[0])
        else:
            # multi match
            self.matchList = matchList
            on_done = functools.partial(self.on_done)
            self.view.window().show_quick_panel(showList, on_done)

    def on_done(self, index):
        if index == -1:
            return
        item = self.matchList[index]
        self.gotoDefinition(item)

    def gotoDefinition(self, item):
        filepath = item["path"]
        loc = item["loc"]
        # if definitionType==1:
        #     # lua
        #     quick_cocos2dx_root=checkQuickxRoot()
        #     if not quick_cocos2dx_root:
        #         return
        #     filepath=os.path.join(quick_cocos2dx_root,filepath)
        # elif definitionType==2:
        #     # cocos2dx
        #     cocos2dx_root=checkCocos2dxRoot()
        #     if not cocos2dx_root:
        #         return
        #     filepath=os.path.join(cocos2dx_root,filepath)
        if os.path.exists(filepath):
            self.view.window().open_file(filepath+":"+str(loc["row"])+":"+str(loc["col"]),sublime.ENCODED_POSITION)
        else:
            sublime.status_message("%s not exists"%(filepath))

    def is_enabled(self):
        return self.view.file_name() and self.view.file_name().endswith(".lua")

    def is_visible(self):
        return self.is_enabled()

VARIABLES = {}
FUNCTIONS = {}
FILE_RELATED = {}

try:
    import helper
except:
    from . import helper

def hasIdentifier(node):
    return "identifier" in node and node["identifier"]

def isTypeNull(node):
    return node["type"] == None

def isTypeIdentifier(node):
    return node["type"] == "Identifier"

def isTypeMemberExpression(node):
    return node["type"] == "MemberExpression"

def getIdentifierName(node):
    try:
        return node["identifier"]["name"]
    except:
        print("Get name from identifier error: ", node)
        return ""

def parse_arguments(parameters):
    results = []
    for node in parameters:
        if "name" in node:
            results.append(node["name"])
        elif "value" in node:
            results.append(node["value"])
    return results

def parse_function_declaration(filename, ast_obj):
    func_name = None
    func_parents = []
    func_args = parse_arguments(ast_obj["parameters"])
    func_loc = helper.get_location(filename, ast_obj["loc"])
    if (not hasIdentifier(ast_obj)) or isTypeNull(ast_obj["identifier"]):
        return
    elif isTypeIdentifier(ast_obj["identifier"]):
        func_name = getIdentifierName(ast_obj)
    elif isTypeMemberExpression(ast_obj["identifier"]):        
        node = ast_obj["identifier"]
        func_name = getIdentifierName(node)
        node = node["base"]
        while isTypeMemberExpression(node):
            func_parents.append(getIdentifierName(node))
            node = node["base"]

    global FUNCTIONS
    global FILE_RELATED
    helper.push_function(FUNCTIONS, func_name, func_parents, func_args, func_loc)
    helper.push_value(FILE_RELATED, filename, func_name)

def parse_assignment_statement(filename, ast_obj):
    if ast_obj["type"] == "AssignmentStatement":
        for v in ast_obj["variables"]:
            if v["type"] == "Identifier":
                global FILE_RELATED
                global VARIABLES
                helper.push_value(VARIABLES, v["name"], helper.get_location(filename, v["loc"]))
                helper.push_value(FILE_RELATED, filename, v["name"])

# def parse_require_statement(filename, ast_obj):
#     if ast_obj["type"] == "CallExpression" and \
#         ast_obj["base"]["type"] == "Identifier" and \
#         ast_obj["base"]["name"] == "require":
#         if ast_obj["arguments"] and \
#             ast_obj["arguments"][0]["type"] == "StringLiteral":

#             required_module = ast_obj["arguments"][0]["value"]
#             required_module = required_module.replace(r".", "/") + ".lua"

#             project_path = get_project_path()

#             if project_path:
#                 global settings
#                 for module_path in settings.lua_package_paths:
#                     module_path = os.path.join(project_path, module_path, required_module)
#                     if os.path.exists(module_path):
#                         parse(module_path)
#                         return;

def iterate_ast(filename, ast_obj):
    if ast_obj["type"] in ["Chunk"]:
        for b in ast_obj["body"]:
            iterate_ast(filename, b)
    elif ast_obj["type"] == "AssignmentStatement":
        parse_assignment_statement(filename, ast_obj)

        for c in ast_obj["init"]:
            iterate_ast(filename, c)
    elif ast_obj["type"] == "CallExpression":
        # parse_require_statement(filename, ast_obj)
        iterate_ast(filename, ast_obj["base"])
    elif ast_obj["type"] == "CallStatement":
        iterate_ast(filename, ast_obj["expression"])
    elif ast_obj["type"] == "MemberExpression":
        iterate_ast(filename, ast_obj["base"])
    elif ast_obj["type"] == "FunctionDeclaration":
        parse_function_declaration(filename, ast_obj)
        for b in ast_obj["body"]:
            iterate_ast(filename, b)






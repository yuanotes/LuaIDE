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
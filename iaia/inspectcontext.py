import inspect
import dis
import readline


def get_frame_source(uplevel=0, stopwords=()):
    frame = inspect.currentframe()
    for i in range(uplevel + 1):
        frame = frame.f_back
    names = []
    for inst in dis.get_instructions(frame.f_code):
        if inst.offset > frame.f_lasti and inst.starts_line:
            break
        if inst.starts_line:
            names = []
        if inst.opname.startswith("STORE"):
            names.append(inst.argval)
    try:
        source = inspect.getsource(frame.f_code)
    except OSError:
        # This might happen when used interactively, try to get history...
        source = get_recent_history()
    for stopword in stopwords:
        if stopword in source:
            source = source[: source.index(stopword)] + " ..."
    if not source:
        source = ", ".join(names) + "="
    else:
        source = source.strip() + "# " + ", ".join(names)
    return source


def get_recent_history():
    length = readline.get_current_history_length()
    if length:
        return readline.get_history_item(length)
    return ""

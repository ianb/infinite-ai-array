import inspect
import dis
import readline


def get_frame_source(uplevel=0):
    frame = inspect.currentframe()
    for i in range(uplevel + 1):
        print("frame", i, uplevel, frame.f_lineno)
        frame = frame.f_back
    print(
        dir(frame),
        frame.f_lasti,
        frame.f_code,
    )
    print(dis.code_info(frame.f_code))
    names = []
    for index, inst in enumerate(dis.get_instructions(frame.f_code)):
        if inst.offset > frame.f_lasti and inst.starts_line:
            break
        if inst.starts_line:
            names = []
        if inst.opname.startswith("STORE"):
            names.append(inst.argval)
        print(index, frame.f_lasti, inst)
    print(names)
    try:
        source = inspect.getsource(frame.f_code)
    except OSError:
        # This might happen when used interactively, try to get history...
        source = get_recent_history()
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

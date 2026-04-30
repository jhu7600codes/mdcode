#!/usr/bin/env python3
import sys
import os
import re
import subprocess
import time
import urllib.request
import urllib.error

# ── variable store ────────────────────────────────────────────────────────────

class VarStore:
    def __init__(self):
        self.globals = {}
        # onetimeVars keyed by depth they were created at
        self.onetimevars = {}  # depth -> {name: value}
        self.autovar_enabled = False
        self.strVar = None
        self.last_log = {}  # command -> log string

    def set(self, name, value):
        self.globals[name] = value

    def set_onetime(self, name, value, depth):
        if depth not in self.onetimevars:
            self.onetimevars[depth] = {}
        self.onetimevars[depth][name] = value

    def get(self, name, depth=None):
        # check onetimeVars for parent depth (depth - 1) if accessing via ##
        if depth is not None:
            parent_depth = depth - 1
            if parent_depth in self.onetimevars and name in self.onetimevars[parent_depth]:
                return self.onetimevars[parent_depth][name]
        if name == "strVar" and self.autovar_enabled:
            return self.strVar
        return self.globals.get(name)

    def clear_onetimevars(self, depth):
        if depth in self.onetimevars:
            del self.onetimevars[depth]

    def set_log(self, command, message):
        key = command + "Log"
        self.globals[key] = message
        self.last_log[command] = message


store = VarStore()

# ── argument parser ───────────────────────────────────────────────────────────

def resolve_value(token, depth=None):
    """resolve a single token: either a |string or a varName"""
    token = token.strip()
    if token.startswith("|"):
        return token[1:].strip()
    else:
        val = store.get(token, depth)
        if val is None:
            return token  # return as-is if not found
        return str(val)

def parse_args(raw, depth=None):
    """
    parse the argument string after the command name.
    handles: | strings, vars, + concat, > assignment, / pipes
    returns (value, assign_to, pipe_rest)
    """
    # split on > for assignment (last one wins)
    assign_to = None
    pipe_rest = None

    # handle / pipe first — split on first /
    if " / " in raw:
        parts = raw.split(" / ", 1)
        raw = parts[0].strip()
        pipe_rest = parts[1].strip()

    # handle > assignment
    if " > " in raw:
        parts = raw.rsplit(" > ", 1)
        raw = parts[0].strip()
        assign_to = parts[1].strip()

    # now resolve the value with + concatenation
    value = resolve_concat(raw, depth)
    return value, assign_to, pipe_rest

def resolve_concat(raw, depth=None):
    """resolve a + concatenated expression"""
    if " + " not in raw:
        return resolve_value(raw, depth)

    parts = raw.split(" + ")
    result = ""
    for i, part in enumerate(parts):
        chunk = resolve_value(part.strip(), depth)
        # add space between parts unless the chunk already has edge spaces
        if i > 0 and result and not result.endswith(" ") and not chunk.startswith(" "):
            result += " "
        result += chunk
    return result

# ── pipe executor ─────────────────────────────────────────────────────────────

def execute_pipe_chain(first_cmd, first_args_raw, pipe_rest, depth):
    """execute a chain of piped commands"""
    result = execute_command(first_cmd, first_args_raw, depth, piped_input=None)
    
    while pipe_rest:
        if " / " in pipe_rest:
            parts = pipe_rest.split(" / ", 1)
            cmd_part = parts[0].strip()
            pipe_rest = parts[1].strip()
        else:
            cmd_part = pipe_rest.strip()
            pipe_rest = None

        # parse cmd and args from cmd_part
        tokens = cmd_part.split(None, 1)
        cmd = tokens[0]
        args_raw = tokens[1] if len(tokens) > 1 else ""
        result = execute_command(cmd, args_raw, depth, piped_input=result)

    return result

# ── commands ──────────────────────────────────────────────────────────────────

def cmd_print(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    if piped_input is not None:
        value = str(piped_input) + " " + value if value else str(piped_input)
    print(value)
    store.set_log("print", "printFinish = success")
    if store.autovar_enabled:
        store.strVar = value
    return value

def cmd_input(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    if piped_input is not None:
        # auto-answer the prompt
        print(f"{value} {piped_input}" if value else piped_input)
        result = str(piped_input)
    else:
        result = input(value + " " if value else "")
    if assign_to:
        store.set(assign_to, result)
    if store.autovar_enabled:
        store.strVar = result
    return result

def cmd_ask(args_raw, depth, piped_input=None):
    return cmd_input(args_raw, depth, piped_input)

def cmd_readFile(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    path = os.path.expanduser(value)
    try:
        with open(path, "r") as f:
            content = f.read()
        log = f"readFile: read {len(content)} bytes from {path}"
        store.set_log("readFile", log)
        if assign_to:
            store.set(assign_to, content)
        if store.autovar_enabled:
            store.strVar = content
        return content
    except FileNotFoundError:
        log = f"readFile: no such file or directory: {path}"
        store.set_log("readFile", log)
        print(log, file=sys.stderr)
        return None
    except PermissionError:
        log = f"readFile: permission denied: {path}"
        store.set_log("readFile", log)
        print(log, file=sys.stderr)
        return None

def cmd_writeFile(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    # format: path > content  OR  path > | string
    # assign_to holds the content here
    if assign_to is None:
        print("writeFile: missing content (use >)", file=sys.stderr)
        return None
    path = os.path.expanduser(value)
    content = assign_to
    # resolve if it's a | string
    if content.startswith("| "):
        content = content[2:]
    else:
        content = str(store.get(content) or content)
    try:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        log = f"writeFile: wrote {len(content)} bytes to {path}"
        store.set_log("writeFile", log)
        if store.autovar_enabled:
            store.strVar = content
        return content
    except Exception as e:
        log = f"writeFile: {e}"
        store.set_log("writeFile", log)
        print(log, file=sys.stderr)
        return None

def cmd_getVar(args_raw, depth, piped_input=None):
    name = args_raw.strip()
    val = store.get(name, depth)
    if val is None:
        log = f"getVar: no variable {name} set"
        store.set_log("getVar", log)
        print(log, file=sys.stderr)
        return None
    store.set_log("getVar", f"getVar: {name} = {val}")
    if store.autovar_enabled:
        store.strVar = val
    return val

def cmd_var(args_raw, depth, piped_input=None):
    raw = args_raw.strip()

    # #var varName (create) | value
    m = re.match(r'(\w+)\s*\(create\)\s*(.*)', raw)
    if m:
        name = m.group(1)
        rest = m.group(2).strip()
        value = resolve_value(rest, depth)
        store.set(name, value)
        store.set_log("var", f"var: created {name} = {value}")
        return value

    # #var varName (edit) | newvalue   or   #var varName (edit) otherVar
    m = re.match(r'(\w+)\s*\(edit\)\s*(.*)', raw)
    if m:
        name = m.group(1)
        rest = m.group(2).strip()
        value = resolve_value(rest, depth)
        if store.get(name) is None:
            log = f"var: no variable {name} set, use (create) instead"
            store.set_log("var", log)
            print(log, file=sys.stderr)
            return None
        store.set(name, value)
        store.set_log("var", f"var: edited {name} = {value}")
        return value

    # #var varName (change) type > onetimeVar
    m = re.match(r'(\w+)\s*\(change\)\s*\w+\s*>\s*(\w+)', raw)
    if m:
        src = m.group(1)
        dest = m.group(2)
        val = store.get(src, depth)
        store.set_onetime(dest, val, depth)
        return val

    # fallback: #var name > dest
    value, assign_to, pipe_rest = parse_args(raw, depth)
    if assign_to:
        store.set_onetime(assign_to, value, depth)
    return value

def cmd_os(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    try:
        result = subprocess.check_output(value, shell=True, text=True).strip()
        log = f"os: ran `{value}`"
        store.set_log("os", log)
        if assign_to:
            store.set(assign_to, result)
        if store.autovar_enabled:
            store.strVar = result
        return result
    except subprocess.CalledProcessError as e:
        log = f"os: command failed: {value}"
        store.set_log("os", log)
        print(log, file=sys.stderr)
        return None

def cmd_env(args_raw, depth, piped_input=None):
    value, assign_to, pipe_rest = parse_args(args_raw, depth)
    result = os.environ.get(value, "")
    if not result:
        log = f"env: variable {value} not set"
        store.set_log("env", log)
        print(log, file=sys.stderr)
    if assign_to:
        store.set(assign_to, result)
    if store.autovar_enabled:
        store.strVar = result
    return result

def cmd_exit(args_raw, depth, piped_input=None):
    value, _, _ = parse_args(args_raw, depth)
    try:
        sys.exit(int(value))
    except (ValueError, TypeError):
        sys.exit(0)

def cmd_wait(args_raw, depth, piped_input=None):
    value, _, _ = parse_args(args_raw, depth)
    try:
        time.sleep(float(value))
    except (ValueError, TypeError):
        pass

def cmd_math(args_raw, depth, piped_input=None):
    # extract assignment first
    assign_to = None
    raw = args_raw.strip()
    if " > " in raw:
        parts = raw.rsplit(" > ", 1)
        raw = parts[0].strip()
        assign_to = parts[1].strip()
    # strip leading | if present
    if raw.startswith("| "):
        raw = raw[2:].strip()
    elif raw.startswith("|"):
        raw = raw[1:].strip()
    try:
        result = str(eval(raw, {"__builtins__": {}}))
        if assign_to:
            store.set(assign_to, result)
        if store.autovar_enabled:
            store.strVar = result
        return result
    except Exception as e:
        log = f"math: error: {e}"
        store.set_log("math", log)
        print(log, file=sys.stderr)
        return None

def cmd_req(args_raw, depth, piped_input=None):
    value, assign_to, _ = parse_args(args_raw, depth)
    try:
        with urllib.request.urlopen(value) as r:
            result = r.read().decode()
        if assign_to:
            store.set(assign_to, result)
        if store.autovar_enabled:
            store.strVar = result
        return result
    except Exception as e:
        log = f"req: {e}"
        store.set_log("req", log)
        print(log, file=sys.stderr)
        return None

def cmd_import(args_raw, depth, piped_input=None):
    lib = args_raw.strip()
    if lib == "lib-autoVar":
        store.autovar_enabled = True
    elif lib == "lib-visual":
        store.globals["__lib_visual__"] = True
    # lib-mdcode is always active, nothing extra to do
    return None

def cmd_if(args_raw, depth, piped_input=None):
    value, _, _ = parse_args(args_raw, depth)
    # evaluate condition: supports "var = value" and "var != value"
    m = re.match(r'(\w+)\s*(=|!=|>|<|>=|<=)\s*(.+)', value)
    if m:
        lhs = store.get(m.group(1), depth) or m.group(1)
        op = m.group(2)
        rhs = m.group(3).strip()
        ops = {"=": lambda a,b: str(a)==str(b), "!=": lambda a,b: str(a)!=str(b),
               ">": lambda a,b: float(a)>float(b), "<": lambda a,b: float(a)<float(b),
               ">=": lambda a,b: float(a)>=float(b), "<=": lambda a,b: float(a)<=float(b)}
        try:
            result = ops[op](lhs, rhs)
        except:
            result = False
        store.set("__if_result__", result)
        return result
    store.set("__if_result__", bool(value))
    return bool(value)

def cmd_else(args_raw, depth, piped_input=None):
    return not store.get("__if_result__")

def cmd_loop(args_raw, depth, piped_input=None):
    # basic: #loop | 5  or  #loop varName
    value, _, _ = parse_args(args_raw, depth)
    try:
        return int(value)
    except:
        return 0

def cmd_func(args_raw, depth, piped_input=None):
    # define a function name — body handled by interpreter
    name = args_raw.strip()
    store.set(f"__func_{name}__", depth)
    return name

def cmd_err(args_raw, depth, piped_input=None):
    value, _, _ = parse_args(args_raw, depth)
    # check if last operation had an error
    last_log_values = list(store.last_log.values())
    had_error = any("error" in v.lower() or "no such" in v.lower() or "permission" in v.lower()
                    for v in last_log_values[-3:]) if last_log_values else False
    store.set("__err_triggered__", had_error)
    return had_error

# ── command dispatch ──────────────────────────────────────────────────────────

COMMANDS = {
    "print": cmd_print,
    "input": cmd_input,
    "ask": cmd_ask,
    "readFile": cmd_readFile,
    "writeFile": cmd_writeFile,
    "getVar": cmd_getVar,
    "var": cmd_var,
    "os": cmd_os,
    "env": cmd_env,
    "exit": cmd_exit,
    "wait": cmd_wait,
    "math": cmd_math,
    "req": cmd_req,
    "import": cmd_import,
    "if": cmd_if,
    "else": cmd_else,
    "loop": cmd_loop,
    "func": cmd_func,
    "err": cmd_err,
}

def execute_command(cmd, args_raw, depth, piped_input=None):
    fn = COMMANDS.get(cmd)
    if fn is None:
        print(f"mdcode: unknown command: {cmd}", file=sys.stderr)
        return None
    return fn(args_raw.strip(), depth, piped_input)

# ── lib-visual ────────────────────────────────────────────────────────────────

def run_visual(title, topbar_items, navbar_items, webview_url):
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2, Gdk

        show_topbar = topbar_items is not None
        start_url = webview_url or "about:blank"

        win = Gtk.Window()
        win.set_title(title)
        win.set_default_size(1100, 700)
        win.connect("destroy", Gtk.main_quit)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        win.add(vbox)

        webview = WebKit2.WebView()

        if show_topbar:
            bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            bar.set_margin_start(10)
            bar.set_margin_end(10)
            bar.set_margin_top(5)
            bar.set_margin_bottom(5)

            # css styling
            css = b"""
            .topbar { background: #2a2a2a; }
            .nav-btn { background: #3a3a3a; color: #eee; border: 1px solid #555;
                       border-radius: 4px; padding: 2px 10px; font-size: 13px; }
            .nav-btn:hover { background: #4a4a4a; }
            .title-lbl { color: #fff; font-weight: bold; font-size: 14px; }
            .nav-text { color: #ccc; font-size: 13px; }
            .nav-warn { color: #f0a500; font-size: 12px; }
            """
            provider = Gtk.CssProvider()
            provider.load_from_data(css)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            bar_frame = Gtk.Box()
            bar_frame.get_style_context().add_class("topbar")
            bar_frame.pack_start(bar, True, True, 0)

            # title
            lbl = Gtk.Label(label=title)
            lbl.get_style_context().add_class("title-lbl")
            bar.pack_start(lbl, False, False, 4)

            sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            bar.pack_start(sep, False, False, 4)

            for item in navbar_items:
                itype = item[0]; itext = item[1]
                if itype == "button":
                    action = item[2] if len(item) > 2 else None
                    btn = Gtk.Button(label=itext)
                    btn.get_style_context().add_class("nav-btn")
                    if action and action[0] == "gotoWeb":
                        url = action[1]
                        btn.connect("clicked", lambda _, u=url: webview.load_uri(u))
                    bar.pack_start(btn, False, False, 0)
                elif itype == "menu":
                    label = itext
                    mitems = item[2] if len(item) > 2 else []
                    btn = Gtk.MenuButton(label=label)
                    btn.get_style_context().add_class("nav-btn")
                    menu = Gtk.Menu()
                    for mlabel, murl in mitems:
                        mi = Gtk.MenuItem(label=mlabel)
                        mi.connect("activate", lambda _, u=murl: webview.load_uri(u))
                        menu.append(mi)
                    menu.show_all()
                    btn.set_popup(menu)
                    bar.pack_start(btn, False, False, 0)
                elif itype == "text":
                    lbl2 = Gtk.Label(label=itext)
                    lbl2.get_style_context().add_class("nav-text")
                    bar.pack_start(lbl2, False, False, 0)
                elif itype == "warning":
                    lbl3 = Gtk.Label(label=f"⚠ {itext}")
                    lbl3.get_style_context().add_class("nav-warn")
                    bar.pack_start(lbl3, False, False, 0)

            # spacer + refresh
            bar.pack_start(Gtk.Label(), True, True, 0)
            ref = Gtk.Button(label="↻")
            ref.get_style_context().add_class("nav-btn")
            ref.connect("clicked", lambda _: webview.reload())
            bar.pack_end(ref, False, False, 0)

            vbox.pack_start(bar_frame, False, False, 0)
            sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            vbox.pack_start(sep2, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(webview)
        vbox.pack_start(scroll, True, True, 0)

        webview.load_uri(start_url)
        win.show_all()
        Gtk.main()

    except Exception as e:
        print(f"visual error: {e}")
        import traceback; traceback.print_exc()


def cmd_visual(title, children):
    """
    children: list of (depth, cmd, args_raw) for the visual block
    parse topbar, navbar, webview from children
    """
    topbar_items = None  # None = hidden
    navbar_items = []
    webview_url = None

    base_depth = None

    for depth, cmd, args_raw in children:
        if base_depth is None:
            base_depth = depth

        if cmd == "topbar":
            if "(ignore)" in args_raw:
                topbar_items = None
            else:
                topbar_items = []

        elif cmd == "navbar":
            parts = args_raw.split("|")
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if part.startswith("(button)") and "(gotoWeb)" in part:
                    rest = part[len("(button)"):].strip()
                    label, url = rest.split("(gotoWeb)")
                    navbar_items.append(("button", label.strip(), ("gotoWeb", url.strip())))
                elif part.startswith("(button)") and "(menu)" in part:
                    rest = part[len("(button)"):].strip()
                    label, menu_raw = rest.split("(menu)", 1)
                    menu_items = []
                    for entry in menu_raw.split(","):
                        entry = entry.strip()
                        if " > " in entry:
                            mlabel, murl = entry.split(" > ", 1)
                            menu_items.append((mlabel.strip(), murl.strip()))
                    navbar_items.append(("menu", label.strip(), menu_items))
                elif part.startswith("(button)"):
                    navbar_items.append(("button", part[len("(button)"):].strip()))
                elif part.startswith("(text)"):
                    navbar_items.append(("text", part[len("(text)"):].strip()))
                elif part.startswith("(warning)"):
                    navbar_items.append(("warning", part[len("(warning)"):].strip()))
        elif cmd == "webview":
            val = args_raw.strip()
            if val.startswith("| "):
                val = val[2:]
            webview_url = val

    run_visual(title, topbar_items, navbar_items, webview_url)


# ── parser ────────────────────────────────────────────────────────────────────

def parse_line(line):
    """returns (depth, command, args_raw) or None if not a command"""
    m = re.match(r'^(#+)\s*(\w+)\s*(.*)', line)
    if not m:
        return None
    depth = len(m.group(1))
    command = m.group(2)
    args_raw = m.group(3).strip()
    return depth, command, args_raw

def run_file(path):
    with open(path, "r") as f:
        lines = f.readlines()

    parsed = []
    for line in lines:
        line = line.rstrip()
        if not line or not line.startswith("#"):
            continue
        result = parse_line(line)
        if result:
            parsed.append(result)

    def exec_block(parsed, start, end):
        """execute a slice of parsed lines, returns early if exit called"""
        i = start
        # stack of (skip_depth) — skip children deeper than this
        skip_stack = []

        while i < end:
            depth, cmd, args_raw = parsed[i]

            # skip children of a failed conditional
            if skip_stack and depth > skip_stack[-1]:
                i += 1
                continue
            # pop skip when we return to same or lower depth
            while skip_stack and depth <= skip_stack[-1]:
                skip_stack.pop()

            # handle pipe chains (skip for math since / is division)
            if " / " in args_raw and cmd != "math":
                parts = args_raw.split(" / ", 1)
                execute_pipe_chain(cmd, parts[0].strip(), parts[1].strip(), depth)
                i += 1
                continue

            # handle visual block
            if cmd == "visual":
                title_raw = args_raw.strip()
                if title_raw.startswith("| "):
                    title_raw = title_raw[2:]
                # collect children
                body_start = i + 1
                body_end = body_start
                while body_end < end and parsed[body_end][0] > depth:
                    body_end += 1
                children = parsed[body_start:body_end]
                cmd_visual(title_raw, children)
                i = body_end
                continue

            # handle loop — find its body and repeat
            if cmd == "loop":
                iterations = execute_command(cmd, args_raw, depth)
                iterations = int(iterations) if iterations else 0
                # find body: all lines deeper than this depth
                body_start = i + 1
                body_end = body_start
                while body_end < end and parsed[body_end][0] > depth:
                    body_end += 1
                for _ in range(iterations):
                    exec_block(parsed, body_start, body_end)
                i = body_end
                continue

            result = execute_command(cmd, args_raw, depth)

            if cmd in ("if", "else", "err") and not result:
                skip_stack.append(depth)

            i += 1

    exec_block(parsed, 0, len(parsed))

# ── entrypoint ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3 or sys.argv[1] != "run":
        print("usage: python mdcode.py run <file.md>")
        sys.exit(1)

    path = sys.argv[2]
    if not os.path.exists(path):
        print(f"mdcode: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    run_file(path)

if __name__ == "__main__":
    main()

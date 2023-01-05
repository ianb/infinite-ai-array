import sys
from .findimports import find_imports
import subprocess
from .gptclient import gpt_client
import re
import os
import traceback

package_names_for_module = {
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
}


class MagicModule:
    def __init__(self, gpt_engine="text-davinci-003"):
        self.gpt_engine = gpt_engine
        # FIXME: all code appears to be in <string> and can't
        # be shown in tracebacks. Setting __file__ here doesn't
        # help, but sure what the answer is
        self.ns = {}
        self.existing = {}

    def __getattr__(self, name):
        if name not in self.existing:
            self.existing[name] = MagicFunction(self, name)
        return self.existing[name]


class MagicFunction:
    def __init__(self, module, name):
        self.module = module
        self.name = name
        self.verbose = bool(os.environ.get("IAIA_VERBOSE"))
        self.n = int(os.environ.get("IAIA_MAGIC_ITERATIONS") or 1)
        self.sources = {}
        self.funcs = {}
        self.imports = {}

    def __str__(self):
        if not self.sources:
            return "# Unevaluated magic function"
        if (len(self.sources)) == 1:
            return self.sources[list(self.sources.keys())[0]]
        parts = ["# Magic function with multiple signatures:", *self.sources.values()]
        return "\n".join(parts)

    def __repr__(self):
        sigs = []
        for source in self.sources.values():
            params = "..."
            match = re.findall(r"def \w+\((.*)\):", source)
            if match:
                params = match[0]
            sigs.append(f"({params})")
        sigs = " or ".join(sigs)
        return f"<iaia.maigic.{self.name}{sigs}>"

    def __call__(self, *args, **kw):
        key = self.call_key(*args, **kw)
        if key not in self.funcs:
            self.make_functions(*args, **kw)
        exc = None
        for func_i, func in self.funcs[key].items():
            try:
                return func(*args, **kw)
            except Exception as e:
                exc = e
            print(f"Attempting to fix exception {exc} in func {func_i}...")
            func = self.fix_function(func_i, exc, *args, **kw)
            return func(*args, **kw)

    def call_key(self, *args, **kw):
        return tuple([len(args), *sorted(kw.keys())])

    def format_type_for_prompt(self, arg):
        """
        Format arguments for the prompt, adding info about function args
        """
        name = type(arg).__name__
        if name == "function":
            arg_count = arg.__code__.co_argcount
            return "Callable[" + ", ".join(["Any"] * arg_count) + "]"
        return name

    def format_signature_for_compile(self, signature: str):
        """
        Format function signature so it's compilable by Python
        """
        return re.sub(": Callable\[.*\]", "", signature)

    def make_prompt(self, *args, **kw):
        sig = []
        for i, arg in enumerate(args):
            arg_name = arg.__name__ if hasattr(arg, "__name__") else f"arg{i + 1}"
            sig.append(f"{arg_name}: {self.format_type_for_prompt(arg)}")
        if kw:
            sig.append("*")
        for name, arg in kw.items():
            sig.append(f"{name}: {self.format_type_for_prompt(arg)}")
        signature = f"{self.name}({', '.join(sig)})"
        source = f"def {signature}:"
        prompt = f"""\
Create a function named `{self.name}`:

```
{source}"""
        return prompt, source

    def get_completions(self, prompt, signature):
        response = gpt_client.create_completion(
            engine=self.module.gpt_engine,
            prompt=prompt,
            max_tokens=2000,
            temperature=0,
            stop=["``"],
            n=self.n,
        )
        return [
            self.format_signature_for_compile(signature) + "\n" + choice.text
            for choice in response.choices
        ]

    def make_functions(self, *args, **kw):
        key = self.call_key(*args, **kw)
        prompt, signature = self.make_prompt(*args, **kw)
        sources = self.get_completions(prompt, signature)
        for source_i, source in enumerate(sources):
            if self.verbose:
                print(f"Compiling function index {source_i}... {source}")
            func = self.compile_function(key, source)
            self.sources[key] = self.sources.get(key, dict())
            self.funcs[key] = self.funcs.get(key, dict())
            self.sources[key][source_i] = source
            self.funcs[key][source_i] = func

    def compile_function(self, key, source):
        self.imports[key] = find_imports(source)
        missing = []
        for name in self.imports[key]:
            try:
                __import__(name)
            except ImportError:
                missing.append(name)
        if missing:
            to_install = [package_names_for_module.get(m, m) for m in missing]
            print("Missing imports:", ", ".join(missing))
            print("  To install (guessing):")
            print("     pip install", " ".join(to_install))
            print("Do it now? [y/N]")
            if input().lower() == "y":
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        *to_install,
                    ]
                )
        exec(source, self.module.ns)
        func = self.module.ns[self.name]
        # FIXME: this does set the filename, but the text isn't there so
        # it doesn't let the code show up in tracebacks:
        func.__code__ = func.__code__.replace(co_filename="magic.py")
        return func

    def fix_function(self, func_i, exc, *args, **kw):
        key = self.call_key(*args, **kw)
        source = self.sources[key][func_i]
        tb = traceback.extract_tb(exc.__traceback__)
        line = "?"
        for frame in tb:
            if frame.filename == "magic.py":
                line = source.splitlines()[frame.lineno - 1]
                break
        prompt = f"""\
The following function throws an exception {exc.__class__.__name__}: {exc}
At the line `{line.strip()}`

```
{source}
```

The same function but with the {exc.__class__.__name__} exception fixed:

```"""
        response = gpt_client.create_completion(
            engine=self.module.gpt_engine,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            stop=["``"],
        )
        source = response.choices[0].text
        func = self.compile_function(key, source)
        self.sources[key][func_i] = source
        self.funcs[key][func_i] = func
        return func

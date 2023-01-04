import sys
from .findimports import find_imports
import subprocess
from .gptclient import gpt_client
import re
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
            self.make_function(*args, **kw)
        exc = None
        try:
            return self.funcs[key](*args, **kw)
        except Exception as e:
            exc = e
        print(f"Attempting to fix exception {exc}...")
        self.fix_function(exc, *args, **kw)
        return self.funcs[key](*args, **kw)

    def call_key(self, *args, **kw):
        return tuple([len(args), *sorted(kw.keys())])

    def make_prompt(self, *args, **kw):
        sig = []
        for i, arg in enumerate(args):
            sig.append(f"arg{i + 1}: {type(arg).__name__}")
        if kw:
            sig.append("*")
        for name, arg in kw.items():
            sig.append(f"{name}: {type(arg).__name__}")
        signature = f"{self.name}({', '.join(sig)})"
        source = f"def {signature}:"
        prompt = f"""\
Create a function named `{self.name}`:

```
{source}"""
        return prompt, source

    def get_completion(self, prompt, signature):
        response = gpt_client.create_completion(
            engine=self.module.gpt_engine,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            stop=["```"],
        )
        return signature + "\n" + response.choices[0].text

    def make_function(self, *args, **kw):
        key = self.call_key(*args, **kw)
        prompt, signature = self.make_prompt(*args, **kw)
        source = self.get_completion(prompt, signature)
        self.compile_function(key, source)

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
        self.sources[key] = source
        exec(source, self.module.ns)
        func = self.module.ns[self.name]
        # FIXME: this does set the filename, but the text isn't there so
        # it doesn't let the code show up in tracebacks:
        func.__code__ = func.__code__.replace(co_filename="magic.py")
        self.funcs[key] = self.module.ns[self.name]

    def fix_function(self, exc, *args, **kw):
        key = self.call_key(*args, **kw)
        source = self.sources[key]
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
            stop=["```"],
        )
        source = response.choices[0].text
        self.compile_function(key, source)

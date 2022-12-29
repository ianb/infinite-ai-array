import sys
from .findimports import find_imports
import subprocess
from .gptclient import gpt_client
import re

package_names_for_module = {
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
}


class MagicModule:
    def __init__(self, gpt_engine="text-davinci-003"):
        self.gpt_engine = gpt_engine
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
            print("  To install (gessing):")
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
        self.funcs[key] = self.module.ns[self.name]

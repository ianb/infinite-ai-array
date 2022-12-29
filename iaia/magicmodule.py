import sys
from .findimports import find_imports
import subprocess
from .gptclient import gpt_client

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
        self.source = None
        self.func = None
        self.imports = None

    def __call__(self, *args, **kw):
        if self.func is None:
            self.make_function(*args, **kw)
        return self.func(*args, **kw)

    def make_prompt(self, *args, **kw):
        sig = []
        for i, arg in enumerate(args):
            sig.append(f"arg{i + 1}: {type(arg).__name__}")
        if kw:
            sig.append("*, ")
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
        response = gpt_client.completion_create(
            engine=self.module.gpt_engine,
            prompt=prompt,
            max_tokens=1000,
            temperature=0.1,
            stop=["```"],
        )
        return signature + "\n" + response.choices[0].text

    def make_function(self, *args, **kw):
        prompt, signature = self.make_prompt(*args, **kw)
        source = self.get_completion(prompt, signature)
        self.imports = find_imports(source)
        missing = []
        for name in self.imports:
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
        self.source = source
        exec(source, self.module.ns)
        self.func = self.module.ns[self.name]

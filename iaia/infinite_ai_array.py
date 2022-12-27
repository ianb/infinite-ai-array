"""Main module."""
from collections.abc import MutableSequence
import openai
import inspect
import re
import readline
import dis


class InfiniteAIArray(MutableSequence):
    def __init__(
        self, _iterable=None, *, gpt_key=None, gpt_engine="text-davinci-003", uplevel=0
    ):
        self._list = list(_iterable or [])
        self._waiting_items = []
        self.gpt_key = gpt_key
        self.gpt_engine = gpt_engine
        self.max_gpt_context = 10
        self._max_easy_grow = 10
        self._max_tries = 3
        self._prompt_context = self._get_frame_source(uplevel)
        self._type = None
        if self._list:
            self._guess_type(self._list)

    def _guess_type(self, list):
        if not list:
            return
        isnum = True
        for item in list:
            if not self._is_num(item):
                isnum = False
                break
        if isnum:
            self._type = "number"
        else:
            self._type = "str"

    _is_num_re = re.compile(r"^\s*[+-]?\d+(\.\d+)?\s*$")

    def _is_num(self, s):
        return isinstance(s, (int, float)) or (
            isinstance(s, str) and self._is_num_re.match(s)
        )

    def _as_num(self, s):
        if not isinstance(s, str):
            return s
        if "." in s:
            try:
                return float(s)
            except ValueError:
                return s
        try:
            return int(s)
        except ValueError:
            return s

    def _coerce_type(self, s):
        if self._type == "number":
            return self._as_num(s)
        return s

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self) + self._max_easy_grow)
            if stop > len(self._list):
                self._get_next_item(stop)
            return [self[i] for i in range(start, stop, step)]
        if index < len(self._list):
            return self._list[index]
        else:
            self._get_next_item(index)
            return self._list[index]

    def __setitem__(self, index, value):
        self._list[index] = value

    def __delitem__(self, index):
        del self._list[index]

    def __repr__(self):
        source = repr(self._list)
        return source[:-1] + ", ...]"

    def insert(self, index, value):
        self._list.insert(index, value)

    def __len__(self):
        return len(self._list)

    def _get_frame_source(self, uplevel=0):
        frame = inspect.currentframe()
        for i in range(uplevel + 2):
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
            source = self._get_recent_history()
        if not source:
            source = "[" + ", ".join(names) + "]"
        else:
            source = source.strip() + "# " + ", ".join(names)
        return source

    def _get_recent_history(self):
        length = readline.get_current_history_length()
        if length:
            return readline.get_history_item(length)
        return ""

    def _get_next_item(self, upto):
        tries = self._max_tries
        while True:
            needed = upto - len(self._list) + 1
            print("checking", len(self._list), upto, needed, len(self._waiting_items))
            if needed <= len(self._waiting_items):
                self._list.extend(self._waiting_items[:needed])
                del self._waiting_items[:needed]
                return
            if tries <= 0:
                raise IndexError("No more items available")
            nums = []
            last_num = 0
            for i, item in enumerate(self._list[(-self.max_gpt_context) :]):
                nums.append(f"{i + 1}. {item}")
                last_num = i
            nums = "\n".join(nums)
            prompt = f"""A list of {last_num + needed} items, created with the code `{self._prompt_context}`:

{nums}
{last_num + 1}.
    """.strip()
            print("prompt:", prompt)
            response = openai.Completion.create(
                engine=self.gpt_engine,
                prompt=prompt,
                temperature=0.5,
                max_tokens=24,
                # top_p=1,
                # frequency_penalty=0,
                # presence_penalty=0,
            )
            text = response.choices[0].text
            print("response:", response, text)
            result = []
            for items in [self._fix_line(line) for line in text.splitlines()]:
                result.extend(items)
            print("result:", result)
            ## The last item was cut off:
            if response.choices[0].finish_reason == "length" and result:
                result.pop()
            if self._type is None:
                self._guess_type(result)
            self._waiting_items.extend(self._coerce_type(r) for r in result)
            tries -= 1

    line_re = re.compile(r"^\d+\.\s*")

    def _fix_line(self, line):
        text = self.line_re.sub("", line.strip()).strip()
        if text.startswith("["):
            text = text.strip("[").strip("]")
            return [item.strip() for item in text.split(",")]
        if not text:
            return []
        return [text]

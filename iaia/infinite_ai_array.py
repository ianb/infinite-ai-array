"""Main module."""
from collections.abc import MutableSequence, MutableMapping
import openai
import re
from .inspectcontext import get_frame_source
from .coercion import is_num, as_num
import time


class InfiniteAIArray(MutableSequence):
    def __init__(
        self,
        _iterable=None,
        *,
        gpt_key=None,
        gpt_engine="text-davinci-003",
        uplevel=0,
        rate_limit=5,
    ):
        self._list = list(_iterable or [])
        self._waiting_items = []
        self.gpt_key = gpt_key
        self.gpt_engine = gpt_engine
        self.max_gpt_context = 10
        self.rate_limit = rate_limit
        self._last_times = []
        self._max_easy_grow = 10
        self._max_tries = 3
        self._prompt_context = get_frame_source(uplevel + 1)
        self._type = None
        if self._list:
            self._guess_type(self._list)

    def _guess_type(self, list):
        if not list:
            return
        isnum = True
        for item in list:
            if not is_num(item):
                isnum = False
                break
        if isnum:
            self._type = "number"
        else:
            self._type = "str"

    def _coerce_type(self, s):
        if self._type == "number":
            return as_num(s)
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

    def _get_next_item(self, upto):
        tries = self._max_tries
        self._last_times = [t for t in self._last_times if t > time.time() - 1]
        while True:
            needed = upto - len(self._list) + 1
            print("checking", len(self._list), upto, needed, len(self._waiting_items))
            if needed <= len(self._waiting_items):
                self._list.extend(self._waiting_items[:needed])
                del self._waiting_items[:needed]
                return
            if tries <= 0:
                raise IndexError("No more items available")
            if len(self._last_times) >= self.rate_limit:
                raise IndexError("Rate limit exceeded")
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
            self._last_times.append(time.time())
            text = response.choices[0].text
            print("response:", response, text)
            result = []
            for items in [self._fix_line(line) for line in text.splitlines()]:
                result.extend(items)
            print("result:", result)
            # The last item was cut off:
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


class InfiniteAIDict(MutableMapping):
    def __init__(
        self,
        _iterable=None,
        *,
        gpt_key=None,
        gpt_engine="text-davinci-003",
        uplevel=0,
        ratelimit=5,
    ):
        self._dict = dict(_iterable or ())
        self.gpt_key = gpt_key
        self.gpt_engine = gpt_engine
        self.rate_limit = ratelimit
        self.max_gpt_context = 10
        self._last_times = []
        print("what up?", uplevel)
        self._prompt_context = get_frame_source(uplevel + 1)
        self._type = None
        if self._dict:
            self._guess_type(self._dict)

    def _guess_type(self, d):
        if not d:
            return
        isnum = True
        for value in d.values():
            if not is_num(value):
                isnum = False
                break
        if isnum:
            self._type = "number"
        else:
            self._type = "str"

    def _coerce_type(self, s):
        if self._type == "number":
            return as_num(s)
        return s

    def __getitem__(self, key):
        if key in self._dict:
            return self._dict[key]
        else:
            self._get_next_item(key)
            return self._dict[key]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def _get_next_item(self, asking_key):
        self._last_times = [t for t in self._last_times if t > time.time() - 1]
        if len(self._last_times) >= self.rate_limit:
            raise IndexError("Rate limit exceeded")
        items = []
        last_num = 0
        for i, key in enumerate(list(self._dict.keys())[-self.max_gpt_context :]):
            items.append(f"{i + 1}. {key}: {self._dict[key]}")
            last_num = i
        items = "\n".join(items)
        prompt = f"""A list of name: value pairs, created with the code `{self._prompt_context}`:

{items}
{last_num + 1}. {asking_key}:
""".strip()
        print("prompt:", prompt)
        response = openai.Completion.create(
            engine=self.gpt_engine,
            prompt=prompt,
            temperature=0.5,
            max_tokens=24,
            stop=["\n"],
            # top_p=1,
            # frequency_penalty=0,
            # presence_penalty=0,
        )
        self._last_times.append(time.time())
        text = response.choices[0].text
        print("response:", response, text)
        # FIXME: should consider what to do if the last item was cut off
        if self._type is None:
            self._guess_type({asking_key: text})
        self._dict[asking_key] = self._coerce_type(text)

    def __repr__(self):
        source = repr(self._dict)
        return source[:-1] + ", ...}"

"""Main module."""
from collections.abc import MutableSequence, MutableMapping
import re
from .inspectcontext import get_frame_source
from .coercion import is_num, as_num
from .gptclient import gpt_client


class InfiniteAIArray(MutableSequence):
    def __init__(
        self,
        _iterable=None,
        *,
        gpt_key=None,
        gpt_engine="text-davinci-003",
        uplevel=0,
    ):
        self._list = list(_iterable or [])
        self._waiting_items = []
        self.gpt_key = gpt_key
        self.gpt_engine = gpt_engine
        self.max_gpt_context = 10
        self._max_easy_grow = 10
        self._max_tries = 6
        self._prompt_context = get_frame_source(uplevel + 1, [self.__class__.__name__])
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
            if stop >= len(self._list):
                self._get_next_item(stop - 1)
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

    _no_value = ()

    def append(self, /, value=_no_value):
        if value is self._no_value:
            self._get_next_item(len(self._list))
        self._list.append(value)

    def __iter__(self):
        return iter(self._list)

    def forever(self):
        return ArrayIterator(self, -1)

    def insert(self, index, value):
        self._list.insert(index, value)

    def __len__(self):
        return len(self._list)

    def _get_next_item(self, upto):
        tries = self._max_tries
        while True:
            needed = upto - len(self._list) + 1
            if needed <= len(self._waiting_items):
                self._list.extend(self._waiting_items[:needed])
                del self._waiting_items[:needed]
                return
            self._list.extend(self._waiting_items)
            needed -= len(self._waiting_items)
            self._waiting_items = []
            if tries <= 0:
                raise IndexError("No more items available")
            nums = []
            last_num = -1
            for i, item in enumerate(self._list[(-self.max_gpt_context) :]):
                nums.append(f"{i + 1}. {item}")
                last_num = i
            nums = "\n".join(nums)
            prompt = f"""A list of {last_num + needed + 1} items, created with the code `{self._prompt_context}`:

{nums}
{last_num + 2}.
    """.strip()
            response = gpt_client.create_completion(
                engine=self.gpt_engine,
                prompt=prompt,
                temperature=0.5,
                max_tokens=12 * (needed + 1),
                # top_p=1,
                # frequency_penalty=0,
                # presence_penalty=0,
            )
            text = response.choices[0].text
            result = []
            has_empty_last_line = False
            for items in [self._fix_line(line) for line in text.splitlines()]:
                result.extend(items)
                has_empty_last_line = not items
            finish_reason = response.choices[0].finish_reason
            # The last item was cut off:
            if finish_reason == "length" and result and not has_empty_last_line:
                result.pop()
            if self._type is None:
                self._guess_type(result)
            self._waiting_items.extend(self._coerce_type(r) for r in result)
            tries -= 1

    line_re = re.compile(r"^\d+\.\s*")
    assignment_re = re.compile(r"^\s*\w+\s*=\s*")

    def _fix_line(self, line):
        text = self.line_re.sub("", line.strip()).strip()
        # Sometimes the GPT-3 response has a line like "1. x = 1" or "1. x = [1, 2, 3]".
        match = self.assignment_re.match(text)
        if match:
            text = text[match.end() :]
        if text.startswith("["):
            text = text.strip("[").strip("]")
            return [item.strip() for item in text.split(",")]
        if not text:
            return []
        return [text]


class ArrayIterator:
    def __init__(self, array, how_far_past):
        self.array = array
        self.index = 0
        if how_far_past == -1:
            self.max_index = float("inf")
        else:
            self.max_index = len(array) + how_far_past

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.max_index:
            raise StopIteration
        item = self.array[self.index]
        self.index += 1
        return item


class InfiniteAIDict(MutableMapping):
    def __init__(
        self,
        _iterable=None,
        *,
        gpt_engine="text-davinci-003",
        uplevel=0,
        ratelimit=5,
    ):
        self._dict = dict(_iterable or ())
        self.gpt_engine = gpt_engine
        self.rate_limit = ratelimit
        # Really we don't need as much context as in a list because these are unordered and a few examples should do:
        self.max_gpt_context = 5
        self._prompt_context = get_frame_source(uplevel + 1, [self.__class__.__name__])
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
        items = []
        last_num = -1
        for i, key in enumerate(list(self._dict.keys())[-self.max_gpt_context :]):
            items.append(f"{i + 1}. {key}: {self._dict[key]}")
            last_num = i
        items = "\n".join(items)
        prompt = f"""A list of name: value pairs, created with the code `{self._prompt_context}`:

{items}
{last_num + 2}. {asking_key}:
""".strip()
        response = gpt_client.create_completion(
            engine=self.gpt_engine,
            prompt=prompt,
            temperature=0.5,
            max_tokens=24,
            stop=["\n"],
            # top_p=1,
            # frequency_penalty=0,
            # presence_penalty=0,
        )
        text = response.choices[0].text
        # FIXME: should consider what to do if the last item was cut off
        text = text.strip()
        if self._type is None:
            self._guess_type({asking_key: text})
        self._dict[asking_key] = self._coerce_type(text)

    def __repr__(self):
        source = repr(self._dict)
        return source[:-1] + ", ...}"

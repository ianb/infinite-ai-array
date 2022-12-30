from pathlib import Path
import openai
import pickle
import hashlib
import re
import time
import os
from collections import namedtuple


class GptClientError(Exception):
    pass


class GptRateLimitError(GptClientError):
    pass


GptRequest = namedtuple("GptRequest", "prompt engine max_tokens temperature stop")


class GptClient:
    def __init__(self):
        self.cache_dir = Path.cwd() / "iaia-cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.rate_limit = 15  # requests per minute
        self._last_times = []
        self.default_engine = "text-davinci-003"
        self.default_temperature = 0.1
        self.verbose = bool(os.environ.get("IAIA_VERBOSE"))
        self._count = 0
        self._tokens = 0
        self._cached_tokens = 0

    def create_completion(
        self, prompt, stop=None, engine=None, temperature=None, max_tokens=12
    ):
        self._count += 1
        if engine is None:
            engine = self.default_engine
        if temperature is None:
            temperature = self.default_temperature
        request = GptRequest(
            prompt=prompt,
            engine=engine,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        val = self.get_cache(request)
        if val is not None:
            if self.verbose:
                self.print_request(request, cached=True)
                self.print_response(val["response"], response_time=0)
            self._cached_tokens += val["response"]["usage"]["total_tokens"]
            return val["response"]
        self._last_times = [t for t in self._last_times if t > time.time() - 60]
        if len(self._last_times) >= self.rate_limit:
            raise GptRateLimitError(
                f"Rate limit of {self.rate_limit} requests per second exceeded"
            )
        self._last_times.append(time.time())

        start = time.time()
        if self.verbose:
            self.print_request(request, cached=False)
        response = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        self._tokens += response["usage"]["total_tokens"]
        response_time = time.time() - start
        full_cache = {
            "prompt": prompt,
            "request": {
                "engine": engine,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stop": stop,
            },
            "response": response,
            "time": response_time,
        }
        self.set_cache(request, full_cache)
        if self.verbose:
            self.print_response(response, response_time=response_time)
        return response

    def get_cache(self, request):
        filename = self.get_cache_filename(request)
        if filename.exists():
            text = filename.read_bytes()
            data = pickle.loads(text)
            return data
        return None

    def set_cache(self, request, data):
        filename = self.get_cache_filename(request)
        text = pickle.dumps(data)
        filename.write_bytes(text)

    title_illegal_re = re.compile(r"[^a-zA-Z0-9_\-]")

    def get_cache_filename(self, request):
        title = request[0][:15]
        title = self.title_illegal_re.sub("_", title)
        serialized = pickle.dumps(str(request))
        h = hashlib.sha1(serialized).hexdigest()
        filename = f"{title}-{h}.pickle"
        return self.cache_dir / f"{filename}"

    def print_request(self, request, cached=False):
        # print("=" * 60)
        parts = []
        if cached:
            parts.append("from cache")
        if request.engine != self.default_engine:
            parts.append(f"engine={request.engine}")
        if request.temperature != self.default_temperature:
            parts.append(f"temperature={request.temperature}")
        print(f"Request {self._count}: {' '.join(parts)}")
        print(request.prompt)
        print("-" * 60, "Response")

    def print_response(self, response, response_time):
        print(response.choices[0]["text"])
        print(f"Stop reason: {response.choices[0]['finish_reason']}")
        if response_time:
            print(f"Response time: {response_time:.2f}s")
        prompt_tokens = response.usage["prompt_tokens"]
        completion_tokens = response.usage["completion_tokens"]
        print(
            f"Tokens used: {prompt_tokens}+{completion_tokens}  total: {self._tokens} + cached: {self._cached_tokens} = {self._tokens + self._cached_tokens} ({self.price(self._tokens)} w/o cache {self.price(self._tokens + self._cached_tokens)})"
        )
        print("=" * 60)

    def price(self, tokens):
        # Simplified from https://openai.com/api/pricing/
        if not tokens:
            return "$0"
        price_per_thousand = 0.0200
        p = tokens * price_per_thousand / 1000
        if p < 0.01:
            return f"${p:.4f}"
        elif p < 0.02:
            return f"${p:.3f}"
        else:
            return f"${p:.2f}"


gpt_client = GptClient()

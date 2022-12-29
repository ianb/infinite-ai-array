=================
Infinite AI Array
=================

.. toc::

.. comment:
        .. image:: https://img.shields.io/pypi/v/infinite_ai_array.svg
                :target: https://pypi.python.org/pypi/infinite_ai_array

        .. image:: https://readthedocs.org/projects/infinite-ai-array/badge/?version=latest
                :target: https://infinite-ai-array.readthedocs.io/en/latest/?version=latest
                :alt: Documentation Status


        .. image:: https://pyup.io/repos/github/ianb/infinite_ai_array/shield.svg
        :target: https://pyup.io/repos/github/ianb/infinite_ai_array/
        :alt: Updates


Do you worry that you'll get to the end of a good list and have nothing more, leaving you sad and starved of data! Worry no more!

How are *YOU* helping to bring AI into your runtimes?
-----------------------------------------------------

I hear this all the time:

* Why are my programs so deterministic? How can I make them more exciting and fresh?
* My lists are small and boring. How can I make them bigger and more interesting?
* My functions were written by humans. Even copying and pasting without thinking is too much work. How can I make them more dangerously unpredictable?
* When I write dictionaries I keep getting `KeyError`. I don't want my computer to tell me what doesn't work, I want to hear answers not problems!

Why this is a solution to your made-up problems
-----------------------------------------------

```python
>>> from iaia import InfiniteAIArray, InfiniteAIDict
>>> coolest_cities_ranked = InfiniteAIArray()
>>> print(coolest_cities_ranked[:5])
['Tokyo, Japan', 'London, England', 'San Francisco, USA', 'Sydney, Australia', 'Barcelona, Spain']
>>> coldest_cities_ranked = InfiniteAIArray()
>>> print(coldest_cities_ranked[:5])
['Yakutsk, Russia', 'Verkhoyansk, Russia', 'Oymyakon, Russia', 'Ulaanbaatar, Mongolia', 'Yellowknife, Canada']
>>> names = InfiniteAIArray(["Bingo", "Spot", "Fido"])
>>> print(names[:5])
['Bingo', 'Spot', 'Fido', 'Rover', 'Daisy']
```

Just ask (for values) and you shall receive (more values in your lists).

Also dictionaries...

```python
>>> from iaia import InfiniteAIDict
>>> city_populations = InfiniteAIDict()
>>> for i, city_name in zip(range(5), coolest_cities_ranked):
>>>     print(f"{i+1}. {city_name:<20} {city_populations[city_name]}")
1. Tokyo, Japan         9.273 million
2. New York City, USA   8.623 million
3. London, UK           8.9 million
4. Singapore, Singapore 5.7 million
5. Seoul, South Korea   9.793 million
```

Strings are cool, but how can I be more daring?
-----------------------------------------------

```python
>>> import iaia.magic
>>> iaia.magic.first_primes(5)
[2, 3, 5]
```

Ugh, typical human error, I didn't make it clearer that I wanted the first 5 primes. What did it do?

```python
>>> print(iaia.magic.first_primes)
def first_primes(arg1: int):
    """
    This function takes an integer argument and returns a list of the first
    prime numbers up to the argument.

    Parameters:
    arg1 (int): The number up to which the prime numbers should be returned.

    Returns:
    list: A list of prime numbers up to the argument.
    """

    prime_list = []
    for num in range(2, arg1 + 1):
        for i in range(2, num):
            if (num % i) == 0:
                break
        else:
            prime_list.append(num)
    return prime_list
```

Ah, it thought I wanted the primes *up to* 5, not 5 primes. Let's be clearer:

```python
>>> iaia.magic.first_primes(count=5)
[2, 3, 5, 7, 11]
```

Exciting stuff...

```python
>>> iaia.magic.fetch_wikipedia_source("Apples")
'#REDIRECT [[Apple]]\n\n{{Redirect category shell|1=\n{{R from plural}}\n}}'
>>> iaia.magic.fetch_wikipedia_source("Apple")
... page source ...
````

At least that's what it'll (probably) do if you have the `requests` library installed. (If you don't it will ask if you want to install it.)

"Nothing in life is free" is false, but for this it is true
-----------------------------------------------------------

All those calls were actually backed by [GPT-3](https://en.wikipedia.org/wiki/GPT-3). GPT-3 costs money. To use it you must [sign up for the API](https://openai.com/api/) and [create an API key](https://beta.openai.com/account/api-keys). Then you can use it like this:

```sh
$ export OPENAAI_API_KEY=sk-...
```

Or while in Python:

```python
>>> import iaia
>>> iaia.set_gpt_key("sk...")
```

Note that any requests will go in `iaia-cache/` and be cached forever.

Seeing what's going on
----------------------

You'll probably like to see what's going on. To do this either:

```sh
$ export IAIA_VERBOSE=1
```

Or while in Python:

```python
>>> import iaia
>>> iaia.set_verbose(True)
```

With this is will print the prompts that create all this data, and the responses received. For some list operations it may make multiple requests.

The result looks like this:

```python
>>> import iaia
>>> iaia.set_verbose(True)
>>> book_recommendations = iaia.InfiniteAIArray()
>>> book_recommendations[:3]
Request 1: temperature=0.5
A list of 5 items, created with the code `book_recommendations = iaia. ...# book_recommendations`:


2.
------------------------------------------------------------ Response
 The Catcher in the Rye by J.D. Salinger
3. To Kill a Mockingbird by Harper
Stop reason: length
Response time: 1.64s
Tokens used: 34+24  total: 58 + cached: 0 = 58 ($0.0012 w/o cache $0.0012)
============================================================
...
['The Catcher in the Rye by J.D. Salinger', 'To Kill a Mockingbird by Harper Lee', '1984 by George Orwell']
```

`InfiniteAIArray`` and `InfiniteAIDict` both look at the call context to understand the purpose of the list, as well as using the contents of the data structure.

`iaia.magic` does *not* use the call context, but it does use the function name, argument types, and keyword names.

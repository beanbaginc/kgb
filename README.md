kgb - Function spies for Python
===============================

Ever deal with a large test suite before, monkey patching functions to figure
out whether it was called as expected? It's a dirty job. If you're not careful,
you can make a mess of things. Leave behind evidence.

kgb's spies will take care of that little problem for you.


What are spies?
---------------

Spies intercept and record calls to functions. They can report on how many times
a function was called and with what arguments. They can allow the function call
to go through as normal, to block it, or to reroute it to another function.

Spies are awesome.

(If you've used [Jasmine](http://pivotal.github.io/jasmine/), you know this.)


Where is kgb used?
------------------

We use kgb at [Beanbag](http://www.beanbaginc.com/) for our
[Review Board](http://www.reviewboard.org/) and
[RBCommons](https://rbcommons.com/) products.

If you use kgb, let us know and we'll add you to a shiny new list on this
page.


Installing kgb
--------------

Before you can use kgb, you need to install it. You can do this by typing:

    $ easy_install kgb

or:

    $ pip install kgb

kgb supports Python 2.5 through 2.7.


Spying for fun and profit
-------------------------

Spying is really easy. There are three ways to initiate a spy.


### 1. Creating a SpyAgency

A SpyAgency manages all your spies. You can create as many or as few as you
want. Generally, you'll create one per unit test run. Then you'll call
`spy_on`, passing in the function you want.

```python
from kgb import SpyAgency


class TopSecretTests(unittest.TestCase):
    def test_mind_control_device(self):
        mcd = MindControlDevice()
        agency = SpyAgency()
        agency.spy_on(mcd.assassinate, call_fake=give_hugs)
```


### 2. Mixing a SpyAgency into your tests

A SpyAgency can be mixed into your test suite, making it super easy to spy
all over the place, discretely, without resorting to a separate agency.
(We call this the "inside job.")

```python
from kgb import SpyAgency


class TopSecretTests(SpyAgency, unittest.TestCase):
    def test_weather_control(self):
        weather = WeatherControlDevice()
        self.spy_on(weather.start_raining)
```


### 3. Using a context manager

If you just want a spy for a quick job, without all that hassle of a full
agency, just use the `spy_on` context manager, like so:

```python
from kgb import spy_on


class TopSecretTests(unittest.TestCase):
    def test_the_bomb(self):
        bomb = Bomb()

        with spy_on(bomb.explode, call_original=False):
            # This won't explode. Phew.
            bomb.explode()
```


A word about functions
----------------------

In Python, there are different types of functions. Spying on a bound method
on a class, or a classmethod, is easy. Internally, we just replace those,
and you don't know the difference.

Standard functions are a different matter. We do some evil tricks to make those
work, but we can't replace them with spies completely. For these functions,
you'll need to access the `spy` attribute on the function. We'll show that
below.

For convenience, we also provide a `spy` on all function types, but you only
*need* to use them for standard functions.


A spy's abilities
-----------------

A spy can do many things. The first thing you need to do is figure out how you
want to use the spy.


### Creating a spy that calls the original function

```python
agency.spy_on(obj.function)
```

When your spy is called, the original function will be called as well.
It won't even know you were there.


### Creating a spy that blocks the function call

```python
agency.spy_on(obj.function, call_original=False)
```

Useful if you want to know that a function was called, but don't want the
original function to actually get the call.


### Creating a spy that reroutes to a fake function

```python
agency.spy_on(obj.function, call_fake=my_fake_function)
```

Fake return values or operations without anybody knowing.


### Stopping a spy operation

```python
# For bound methods...
obj.function.unspy()

# For standard functions...
function.spy.unspy()
```

Do your job and get out.


### Check the call history

```python
# For bound methods...
for call in obj.function.calls:
    print calls.args, calls.kwargs

# For standard functions...
for call in function.spy.calls:
    print calls.args, calls.kwargs
```

See how many times your spy's intercepted a function call, and what was passed.


### Check the last call

```python
# For bound methods...
print obj.function.last_call.args
print obj.function.last_call.kwargs

# For standard functions...
print function.spy.last_call.args
print function.spy.last_call.kwargs
```

Also a good way of knowing whether it's even been called. last_call will be
`None` if nobody's called yet.


### Check if the function was ever called

```python
# For bound methods...
self.assertTrue(obj.function.called)

# For standard functions...
self.assertTrue(function.spy.called)
```

If the function was ever called at all, this will let you know.


### Check if the function was ever called with certain arguments

```python
# For bound methods...
self.assertTrue(obj.function.called_with('foo', bar='baz'))

# For standard functions...
self.assertTrue(function.spy.called_with('foo', bar='baz'))
```

The whole call history will be searched. The arguments provided must match
the call exactly. No mixing of args and kwargs.


### Check if the last call had certain arguments

```python
# For bound methods...
self.assertTrue(obj.function.last_called_with('foo', bar='baz'))

# For standard functions...
self.assertTrue(function.spy.last_called_with('foo', bar='baz'))
```

Just like `called_with`, but only the most recent call be checked.


### Reset all the calls

```python
# For bound methods...
obj.function.reset_calls()

# For standard functions...
function.spy.reset_calls()
```

Wipe away the call history. Nobody will know.

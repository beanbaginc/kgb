===============================
kgb - Function spies for Python
===============================

Ever deal with a large test suite before, monkey patching functions to figure
out whether it was called as expected? It's a dirty job. If you're not careful,
you can make a mess of things. Leave behind evidence.

kgb's spies will take care of that little problem for you.


What are spies?
===============

Spies intercept and record calls to functions. They can report on how many times
a function was called and with what arguments. They can allow the function call
to go through as normal, to block it, or to reroute it to another function.

Spies are awesome.

(If you've used Jasmine_, you know this.)


.. _Jasmine: https://jasmine.github.io/


Where is kgb used?
==================

We use kgb at Beanbag_ for our `Review Board`_ and RBCommons_ products.

If you use kgb, let us know and we'll add you to a shiny new list on this
page.


.. _Beanbag: https://www.beanbaginc.com/
.. _Review Board: https://www.reviewboard.org/
.. _RBCommons: https://rbcommons.com/


Installing kgb
==============

Before you can use kgb, you need to install it. You can do this by typing::

    $ pip install kgb

or::

    $ easy_install kgb

kgb supports Python 2.5 through 2.7 and 3.4 through 3.6.


Spying for fun and profit
=========================

Spying is really easy. There are three ways to initiate a spy.


1. Creating a SpyAgency
-----------------------

A SpyAgency manages all your spies. You can create as many or as few as you
want. Generally, you'll create one per unit test run. Then you'll call
``spy_on()``, passing in the function you want.

.. code-block:: python

    from kgb import SpyAgency


    class TopSecretTests(unittest.TestCase):
        def test_mind_control_device(self):
            mcd = MindControlDevice()
            agency = SpyAgency()
            agency.spy_on(mcd.assassinate, call_fake=give_hugs)


2. Mixing a SpyAgency into your tests
-------------------------------------

A SpyAgency can be mixed into your test suite, making it super easy to spy
all over the place, discretely, without resorting to a separate agency.
(We call this the "inside job.")

.. code-block:: python

    from kgb import SpyAgency


    class TopSecretTests(SpyAgency, unittest.TestCase):
        def test_weather_control(self):
            weather = WeatherControlDevice()
            self.spy_on(weather.start_raining)


3. Using a context manager
--------------------------

If you just want a spy for a quick job, without all that hassle of a full
agency, just use the ``spy_on`` context manager, like so:

.. code-block:: python

    from kgb import spy_on


    class TopSecretTests(unittest.TestCase):
        def test_the_bomb(self):
            bomb = Bomb()

            with spy_on(bomb.explode, call_original=False):
                # This won't explode. Phew.
                bomb.explode()


A spy's abilities
=================

A spy can do many things. The first thing you need to do is figure out how you
want to use the spy.


Creating a spy that calls the original function
-----------------------------------------------

.. code-block:: python

    agency.spy_on(obj.function)


When your spy is called, the original function will be called as well.
It won't even know you were there.


Creating a spy that blocks the function call
--------------------------------------------

.. code-block:: python

    agency.spy_on(obj.function, call_original=False)


Useful if you want to know that a function was called, but don't want the
original function to actually get the call.


Creating a spy that reroutes to a fake function
-----------------------------------------------

.. code-block:: python

    agency.spy_on(obj.function, call_fake=my_fake_function)


Fake return values or operations without anybody knowing.


Stopping a spy operation
------------------------

.. code-block:: python

    obj.function.unspy()


Do your job and get out.


Check the call history
----------------------

.. code-block:: python

    for call in obj.function.calls:
        print(calls.args, calls.kwargs)


See how many times your spy's intercepted a function call, and what was passed.


Check a specific call
---------------------

.. code-block:: python

    # Check the latest call...
    print obj.function.last_call.args
    print obj.function.last_call.kwargs
    print obj.function.last_call.return_value
    print obj.function.last_call.exception

    # For an older call...
    print obj.function.calls[0].args
    print obj.function.calls[0].kwargs
    print obj.function.calls[0].return_value
    print obj.function.calls[0].exception


Also a good way of knowing whether it's even been called. ``last_call`` will
be ``None`` if nobody's called yet.


Check if the function was ever called
-------------------------------------

.. code-block:: python

    self.assertTrue(obj.function.called)


If the function was ever called at all, this will let you know.


Check if the function was ever called with certain arguments
------------------------------------------------------------

.. code-block:: python

    # Check if it was ever called with these arguments...
    self.assertTrue(obj.function.called_with('foo', bar='baz'))

    # Check a specific call...
    self.assertTrue(obj.function.calls[0].called_with('foo', bar='baz'))

    # Check the last call...
    self.assertTrue(obj.function.last_called_with('foo', bar='baz'))


The whole call history will be searched. You can provide the entirety of the
arguments passed to the function, or you can provide a subset. You can pass
positional arguments as-is, or pass them by name using keyword arguments.

Recorded calls always follow the function's original signature, so even if a
keyword argument was passed a positional value, it will be recorded as a
keyword argument.


Check if the function ever returned a certain value
---------------------------------------------------

.. code-block:: python

    # Check if the function ever returned a certain value...
    self.assertTrue(obj.function.returned(42))

    # Check a specific call...
    self.assertTrue(obj.function.calls[0].returned(42))

    # Check the last call...
    self.assertTrue(obj.function.last_returned(42))


Handy for checking if some function ever returned what you expected it to, when
you're not calling that function yourself.


Check if a function ever raised a certain type of exception
-----------------------------------------------------------

.. code-block:: python

    # Check if the function ever raised a certain exception...
    self.assertTrue(obj.function.raised(TypeError))

    # Check a specific call...
    self.assertTrue(obj.function.calls[0].raised(TypeError))

    # Check the last call...
    self.assertTrue(obj.function.last_raised(TypeError))


You can also go a step further by checking the exception's message.

.. code-block:: python

    # Check if the function ever raised an exception with a given message...
    self.assertTrue(obj.function.raised_with_message(
        TypeError,
        "'type' object is not iterable"))

    # Check a specific call...
    self.assertTrue(obj.function.calls[0].raised_with_message(
        TypeError,
        "'type' object is not iterable"))

    # Check the last call...
    self.assertTrue(obj.function.last_raised_with_message(
        TypeError,
        "'type' object is not iterable"))


Reset all the calls
-------------------

.. code-block:: python

    obj.function.reset_calls()


Wipe away the call history. Nobody will know.


FAQ
===

Doesn't this just do what mock does?
------------------------------------

kgb's spies and mock_'s patching are very different from each other. When
patching using mock, you're simply replacing a method on a class with
something that looks like a method, and that works great except you're limited
to methods on classes. You can't override something a top-level function, like
``urllib2.urlopen``.

kgb spies leave the function or method where it is. What it *does* do is
replace the *bytecode* of the function, intercepting calls on a very low
level, recording everything about it, and then passing on the call to the
original function or your replacement function. It's pretty powerful, and
allows you to listen to or override calls you normally would have no control
over.

.. _mock: https://pypi.python.org/pypi/mock


What?! There's no way that's stable.
------------------------------------

It is! It really is! We've been using it for years across a wide variety of
codebases. It's pretty amazing.

Python actually allows this. We're not scanning your RAM and doing terrible
things with it, or something like that. Every function or method in Python has
a ``func_code`` (Python 2) or ``__code__`` (Python 3) attribute, which is
mutable. We can go in and replace the bytecode with something compatible with
the original function.

How we actually do that, well, that's complicated, and you may not want to
know.


Does this work with PyPy?
-------------------------

I'm going to level with you, I was going to say "hell no!", and then decided
to give it a try.

Hell yes! (But only accidentally. YMMV... We'll try to officially support this
later.)


What else do you build?
-----------------------

Lots of things. Check out some of our other `open source projects`_.

.. _open source projects: https://www.beanbaginc.com/opensource/

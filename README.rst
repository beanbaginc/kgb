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

Spies are like mocks, but better. You're not mocking the world. You're
replacing very specific function logic, or listening to functions without
altering them. (See the FAQ below.)


.. _Jasmine: https://jasmine.github.io/


What test platforms are supported?
==================================

Anything Python-based:

* unittest_
* pytest_
* nose_
* nose2_

You can even use it outside of unit tests as part of your application. If you
really want to. (Probably don't do that.)


.. _unittest: https://docs.python.org/3/library/unittest.html
.. _pytest: https://pytest.org
.. _nose: https://nose.readthedocs.io/en/latest/
.. _nose2: https://docs.nose2.io/en/latest/


Where is kgb used?
==================

* `liveswot-api <https://github.com/imranariffin/liveswot-api>`_ --
  REST API Backend for liveswot
* `phabricator-emails
  <https://github.com/mozilla-conduit/phabricator-emails>`_ --
  Mozilla's utilities for converting Phabricator feeds to e-mails
* `projector <https://github.com/brennie/projector>`_ --
  Takes the overhead out of managing repositories and development environments
* `ynab-sdk-python <https://github.com/andreroggeri/ynab-sdk-python>`_ --
  Python implementation of the YNAB API

Plus our own products:

* `Django Evolution <https://django-evolution.readthedocs.io/>`_ --
  An alternative approach to Django database migrations
* `Djblets <https://github.com/djblets/djblets/>`_ --
  An assortment of utilities and add-ons for managing large Django projects
* `Review Board <https://www.reviewboard.org/>`_ --
  Our open source, extensible code review product
* `RBCommons <https://rbcommons.com>`_ --
  Our hosted code review service
* `RBTools <https://www.reviewboard.org/downloads/rbtools/>`_ --
  Command line tools for Review Board
* `Power Pack <https://www.reviewboard.org/powerpack/>`_ --
  Document review, reports, and enterprise SCM integrations for Review Board
* `Review Bot <https://www.reviewboard.org/downloads/reviewbot/>`_ --
  Automated code review add-on for Review Board

If you use kgb, let us know and we'll add you!


Installing kgb
==============

Before you can use kgb, you need to install it. You can do this by typing::

    $ pip install kgb

kgb supports Python 2.7 and 3.6 through 3.11, both CPython and PyPy.


Spying for fun and profit
=========================

Spying is really easy. There are four main ways to initiate a spy.


1. Creating a SpyAgency
-----------------------

A SpyAgency manages all your spies. You can create as many or as few as you
want. Generally, you'll create one per unit test run. Then you'll call
``spy_on()``, passing in the function you want.

.. code-block:: python

    from kgb import SpyAgency


    def test_mind_control_device():
        mcd = MindControlDevice()
        agency = SpyAgency()
        agency.spy_on(mcd.assassinate, call_fake=give_hugs)


2. Mixing a SpyAgency into your tests
-------------------------------------

A ``SpyAgency`` can be mixed into your unittest_-based test suite, making
it super easy to spy all over the place, discretely, without resorting to a
separate agency. (We call this the "inside job.")

.. code-block:: python

    from kgb import SpyAgency


    # Using Python's unittest:
    class TopSecretTests(SpyAgency, unittest.TestCase):
        def test_weather_control(self):
            weather = WeatherControlDevice()
            self.spy_on(weather.start_raining)


    # Using pytest with the "spy_agency" fixture (kgb 7+):
    def test_weather_control(spy_agency):
        weather = WeatherControlDevice()
        spy_agency.spy_on(weather.start_raining)


3. Using a decorator
--------------------

If you're creating a spy that calls a fake function, you can simplify some
things by using the ``spy_for`` decorator:


.. code-block:: python

    from kgb import SpyAgency


    # Using Python's unittest:
    class TopSecretTests(SpyAgency, unittest.TestCase):
        def test_doomsday_device(self):
            dd = DoomsdayDevice()

            @self.spy_for(dd.kaboom)
            def _save_world(*args, **kwargs)
                print('Sprinkles and ponies!')

            # Give it your best shot, doomsday device.
            dd.kaboom()


    # Using pytest:
    def test_doomsday_device(spy_agency):
        dd = DoomsdayDevice()

        @spy_agency.spy_for(dd.kaboom)
        def _save_world(*args, **kwargs)
            print('Sprinkles and ponies!')

        # Give it your best shot, doomsday device.
        dd.kaboom()


4. Using a context manager
--------------------------

If you just want a spy for a quick job, without all that hassle of a full
agency, just use the ``spy_on`` context manager, like so:

.. code-block:: python

    from kgb import spy_on


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

    spy_agency.spy_on(obj.function)


When your spy is called, the original function will be called as well.
It won't even know you were there.


Creating a spy that blocks the function call
--------------------------------------------

.. code-block:: python

    spy_agency.spy_on(obj.function, call_original=False)


Useful if you want to know that a function was called, but don't want the
original function to actually get the call.


Creating a spy that reroutes to a fake function
-----------------------------------------------

.. code-block:: python

    def _my_fake_function(some_param, *args, **kwargs):
        ...

    spy_agency.spy_on(obj.function, call_fake=my_fake_function)

    # Or, in kgb 6+
    @spy_agency.spy_for(obj.function)
    def _my_fake_function(some_param, *args, **kwargs):
        ...


Fake the return values or operations without anybody knowing.


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
    print(obj.function.last_call.args)
    print(obj.function.last_call.kwargs)
    print(obj.function.last_call.return_value)
    print(obj.function.last_call.exception)

    # For an older call...
    print(obj.function.calls[0].args)
    print(obj.function.calls[0].kwargs)
    print(obj.function.calls[0].return_value)
    print(obj.function.calls[0].exception)


Also a good way of knowing whether it's even been called. ``last_call`` will
be ``None`` if nobody's called yet.


Check if the function was ever called
-------------------------------------

Mixing in ``SpyAgency`` into a unittest_-based test suite:

.. code-block:: python

    # Either one of these is fine.
    self.assertSpyCalled(obj.function)
    self.assertTrue(obj.function.called)

    # Or the inverse:
    self.assertSpyNotCalled(obj.function)
    self.assertFalse(obj.function.called)


Or using the pytest_ ``spy_agency`` fixture on kgb 7+:

.. code-block:: python

    spy_agency.assert_spy_called(obj.function)
    spy_agency.assert_spy_not_called(obj.function)


Or using standalone assertion methods on kgb 7+:

.. code-block:: python

    from kgb.asserts import (assert_spy_called,
                             assert_spy_not_called)

    assert_spy_called(obj.function)
    assert_spy_not_called(obj.function)


If the function was ever called at all, this will let you know.


Check if the function was ever called with certain arguments
------------------------------------------------------------

Mixing in ``SpyAgency`` into a unittest_-based test suite:

.. code-block:: python

    # Check if it was ever called with these arguments...
    self.assertSpyCalledWith(obj.function, 'foo', bar='baz')
    self.assertTrue(obj.function.called_with('foo', bar='baz'))

    # Check a specific call...
    self.assertSpyCalledWith(obj.function.calls[0], 'foo', bar='baz')
    self.assertTrue(obj.function.calls[0].called_with('foo', bar='baz'))

    # Check the last call...
    self.assertSpyLastCalledWith(obj.function, 'foo', bar='baz')
    self.assertTrue(obj.function.last_called_with('foo', bar='baz'))

    # Or the inverse:
    self.assertSpyNotCalledWith(obj.function, 'foo', bar='baz')
    self.assertFalse(obj.function.called)


Or using the pytest_ ``spy_agency`` fixture on kgb 7+:

.. code-block:: python

    spy_agency.assert_spy_called_with(obj.function, 'foo', bar='baz')
    spy_agency.assert_spy_last_called_with(obj.function, 'foo', bar='baz')
    spy_agency.assert_spy_not_called_with(obj.function, 'foo', bar='baz')


Or using standalone assertion methods on kgb 7+:

.. code-block:: python

    from kgb.asserts import (assert_spy_called_with,
                             assert_spy_last_called_with,
                             assert_spy_not_called_with)

    assert_spy_called_with(obj.function, 'foo', bar='baz')
    assert_spy_last_called_with(obj.function, 'foo', bar='baz')
    assert_spy_not_called_with(obj.function, 'foo', bar='baz')


The whole callkhistory will be searched. You can provide the entirety of the
arguments passed to the function, or you can provide a subset. You can pass
positional arguments as-is, or pass them by name using keyword arguments.

Recorded calls always follow the function's original signature, so even if a
keyword argument was passed a positional value, it will be recorded as a
keyword argument.


Check if the function ever returned a certain value
---------------------------------------------------

Mixing in ``SpyAgency`` into a unittest_-based test suite:

.. code-block:: python

    # Check if the function ever returned a certain value...
    self.assertSpyReturned(obj.function, 42)
    self.assertTrue(obj.function.returned(42))

    # Check a specific call...
    self.assertSpyReturned(obj.function.calls[0], 42)
    self.assertTrue(obj.function.calls[0].returned(42))

    # Check the last call...
    self.assertSpyLastReturned(obj.function, 42)
    self.assertTrue(obj.function.last_returned(42))


Or using the pytest_ ``spy_agency`` fixture on kgb 7+:

.. code-block:: python

    spy_agency.assert_spy_returned(obj.function, 42)
    spy_agency.assert_spy_returned(obj.function.calls[0], 42)
    spy_agency.assert_spy_last_returned(obj.function, 42)


Or using standalone assertion methods on kgb 7+:

.. code-block:: python

    from kgb.asserts import (assert_spy_last_returned,
                             assert_spy_returned)

    assert_spy_returned(obj.function, 42)
    assert_spy_returned(obj.function.calls[0], 42)
    assert_spy_last_returned(obj.function, 42)


Handy for checking if some function ever returned what you expected it to, when
you're not calling that function yourself.


Check if a function ever raised a certain type of exception
-----------------------------------------------------------

Mixing in ``SpyAgency`` into a unittest_-based test suite:

.. code-block:: python

    # Check if the function ever raised a certain exception...
    self.assertSpyRaised(obj.function, TypeError)
    self.assertTrue(obj.function.raised(TypeError))

    # Check a specific call...
    self.assertSpyRaised(obj.function.calls[0], TypeError)
    self.assertTrue(obj.function.calls[0].raised(TypeError))

    # Check the last call...
    self.assertSpyLastRaised(obj.function, TypeError)
    self.assertTrue(obj.function.last_raised(TypeError))


Or using the pytest_ ``spy_agency`` fixture on kgb 7+:

.. code-block:: python

    spy_agency.assert_spy_raised(obj.function, TypeError)
    spy_agency.assert_spy_raised(obj.function.calls[0], TypeError)
    spy_agency.assert_spy_last_raised(obj.function, TypeError)


Or using standalone assertion methods on kgb 7+:

.. code-block:: python

    from kgb.asserts import (assert_spy_last_raised,
                             assert_spy_raised)

    assert_spy_raised(obj.function, TypeError)
    assert_spy_raised(obj.function.calls[0], TypeError)
    assert_spy_last_raised(obj.function, TypeError)


You can also go a step further by checking the exception's message.

.. code-block:: python

    # Check if the function ever raised an exception with a given message...
    self.assertSpyRaisedWithMessage(
        obj.function,
        TypeError,
        "'type' object is not iterable")
    self.assertTrue(obj.function.raised_with_message(
        TypeError,
        "'type' object is not iterable"))

    # Check a specific call...
    self.assertSpyRaisedWithMessage(
        obj.function.calls[0],
        TypeError,
        "'type' object is not iterable")
    self.assertTrue(obj.function.calls[0].raised_with_message(
        TypeError,
        "'type' object is not iterable"))

    # Check the last call...
    self.assertSpyLastRaisedWithMessage(
        obj.function,
        TypeError,
        "'type' object is not iterable")
    self.assertTrue(obj.function.last_raised_with_message(
        TypeError,
        "'type' object is not iterable"))


Reset all the calls
-------------------

.. code-block:: python

    obj.function.reset_calls()


Wipe away the call history. Nobody will know.


Call the original function
--------------------------

.. code-block:: python

    result = obj.function.call_original('foo', bar='baz')


Super, super useful if you want to use ``call_fake=`` or
``@spy_agency.spy_for`` to wrap a function and track or influence some part of
it, but still want the original function to do its thing. For instance:

.. code-block:: python

    stored_results = []

    @spy_agency.spy_for(obj.function)
    def my_fake_function(*args, **kwargs):
        kwargs['bar'] = 'baz'
        result = obj.function.call_original(*args, **kwargs)
        stored_results.append(result)

        return result


Plan a spy operation
====================

Why start from scratch when setting up a spy? Let's plan an operation.

(Spy operations are only available in kgb 6 or higher.)


Raise an exception when called
------------------------------

.. code-block:: python

   spy_on(pen.emit_poison, op=kgb.SpyOpRaise(PoisonEmptyError()))

Or go nuts, have a different exception for each call (in kgb 6.1+):

.. code-block:: python

   spy_on(pen.emit_poison, op=kgb.SpyOpRaiseInOrder([
       PoisonEmptyError(),
       Kaboom(),
       MissingPenError(),
   ]))


Or return a value
-----------------

.. code-block:: python

   spy_on(our_agent.get_identity, op=kgb.SpyOpReturn('nobody...'))

Maybe a different value for each call (in kgb 6.1+)?

.. code-block:: python

   spy_on(our_agent.get_identity, op=kgb.SpyOpReturnInOrder([
       'nobody...',
       'who?',
       'not telling...',
   ]))


Now for something more complicated.


Handle a call based on the arguments used
-----------------------------------------

If you're dealing with many calls to the same function, you may want to return
different values or only call the original function depending on which
arguments were passed in the call. That can be done with a ``SpyOpMatchAny``
operation.

.. code-block:: python

   spy_on(traps.trigger, op=kgb.SpyOpMatchAny([
       {
           'args': ('hallway_lasers',),
           'call_fake': _send_wolves,
       },
       {
           'args': ('trap_tile',),
           'op': SpyOpMatchInOrder([
               {
                   'call_fake': _spill_hot_oil,
               },
               {
                   'call_fake': _drop_torch,
               },
           ]),
       },
       {
           'args': ('infrared_camera',),
           'kwargs': {
               'sector': 'underground_passage',
           },
           'call_original': False,
       },
   ]))

Any unexpected calls will automatically assert.


Or require those calls in a specific order
------------------------------------------

You can combine that with requiring the calls to be in the order you want
using ``SpyOpMatchInOrder``.

.. code-block:: python

   spy_on(lockbox.enter_code, op=kgb.SpyOpMatchInOrder([
       {
           'args': (1, 2, 3, 4, 5, 6),
           'call_original': False,
       },
       {
           'args': (9, 0, 2, 1, 0, 0),
           'call_fake': _start_countdown,
       },
       {
           'args': (42, 42, 42, 42, 42, 42),
           'op': kgb.SpyOpRaise(Kaboom()),
           'call_original': True,
       },
       {
           'args': (4, 8, 15, 16, 23, 42),
           'kwargs': {
               'secret_button_pushed': True,
           },
           'call_original': True,
       }
   ]))


FAQ
===

Doesn't this just do what mock does?
------------------------------------

kgb's spies and mock_'s patching are very different from each other. When
patching using mock, you're simply replacing a method on a class with
something that looks like a method, and that works great except you're limited
to methods on classes. You can't override a top-level function, like
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

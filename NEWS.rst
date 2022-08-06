============
kgb Releases
============

kgb 7.1.1 (6-August-2022)
=========================

* Small packaging update to include the ``LICENSE`` file.

  No code changes.


kgb 7.1 (4-August-2022)
=======================

* Added support for Python 3.11.


kgb 7 (20-January-2022)
=======================

* Added explicit support for Python 3.10.

* Dropped support for Python 2.6, 3.4, and 3.5.

* kgb now works as a plugin for pytest_.

  Unit tests can use the ``spy_agency`` fixture to have a spy agency created
  and ready for use. Spies will be automatically unregistered when the test
  completes.

* Added snake_case versions of all assertion methods in ``SpyAgency``.

  This includes:

  * ``assert_has_spy``
  * ``assert_spy_call_count``
  * ``assert_spy_called_with``
  * ``assert_spy_called``
  * ``assert_spy_last_called_with``
  * ``assert_spy_last_raised_message``
  * ``assert_spy_last_raised``
  * ``assert_spy_last_returned``
  * ``assert_spy_not_called_with``
  * ``assert_spy_not_called``
  * ``assert_spy_raised_message``
  * ``assert_spy_raised``
  * ``assert_spy_returned``

* Added standalone assertion methods in ``kgb.asserts``.

  This provides all the assertion methods shown above, but as standalone
  methods that can work in any test suite.

* Added a ``func_name=`` argument when setting up spies, to avoid problems
  with bad decorators.

  When spying on an unbound method wrapped in a decorator that doesn't
  preserve the function name, errors could occur.

  In this case, you can pass ``func_name=`` when setting up the spy, telling
  kgb about the original function name it should use.

  This is a special situation. Most spies will not need to set this.

* Updated ``SpyCall.__repr__`` to list keyword arguments in sorted order.

* The package now lists the Python versions that are supported.

  This will help down the road when we begin deprecating older versions of
  Python, ensuring that ``pip`` will install the appropriate version of kgb
  for the version of Python.


.. _pytest: https://pytest.org


kgb 6.1 (24-August-2021)
========================

* Added new ``SpyOpReturnInOrder`` and ``SpyOpRaiseInOrder`` spy operations.

  ``SpyOpReturnInOrder`` takes a list of values to return. Each call made
  will return the next value from that list. An exception will be raised
  if any further calls are made once the list is exhausted.

  ``SpyOpRaiseInOrder`` is similar, but takes a list of exceptions to raise.

  Examples:

  .. code-block:: python

     spy_on(our_agent.get_identity, op=kgb.SpyOpReturnInOrder([
         'nobody...',
         'who?',
         'not telling...',
     ]))

     spy_on(pen.emit_poison, op=kgb.SpyOpRaiseInOrder([
         PoisonEmptyError(),
         Kaboom(),
         MissingPenError(),
     ]))

* ``SpyOpMatchInOrder`` and ``SpyOpMatchAny`` now accept operations in the
  expected calls.

  These can be set through an ``op`` key, instead of setting ``call_fake``
  or ``call_original``.

  For example:

  .. code-block:: python

     spy_on(lockbox.enter_code, op=kgb.SpyOpMatchInOrder([
         {
             'args': (42, 42, 42, 42, 42, 42),
             'op': kgb.SpyOpRaise(Kaboom()),
             'call_original': True,
         },
     ]))

  Any operation can be provided. This also allows for advanced, reusable
  rule sets by nesting, for example, ``SpyOpMatchInOrder`` inside
  ``SpyOpMatchAny``.

* ``UnexpectedCallError`` now lists the call that was made in the error
  message.


kgb 6.0 (3-September-2020)
==========================

* Added a new ``@spy_for`` decorator.

  This is an alternative to defining a function and then calling
  ``spy_on(func, call_fake=...)``. It takes a function or method to spy on
  and an optional owner, much like ``spy_on()``.

  For example:

  .. code-block:: python

     def test_doomsday_device(self):
         dd = DoomsdayDevice()

         @self.spy_for(dd.kaboom)
         def _save_world(*args, **kwargs)
             print('Sprinkles and ponies!')

* Added new support for Spy Operations.

  Spy Operations can be thought of as pre-packaged "fake functions" for a spy,
  which can perform some useful operations. There are a few built-in types:

  * ``SpyOpMatchAny`` allows a caller to provide a list of all possible sets
    of arguments that may be in one or more calls, triggering spy behavior
    for the particular match (allowing ``call_original``/``call_fake`` to be
    conditional on the arguments). Any call not provided in the list will
    raise an ``UnexpectedCallError`` assertion.

  * ``SpyOpMatchInOrder`` is similar to ``SpyOpMatchAny``, but the calls
    must be in the order specified (which is useful for ensuring an order
    of operations).

  * ``SpyOpRaise`` takes an exception instance and raises it when the
    function is called (preventing a caller from having to define a
    wrapping function).

  * ``SpyOpReturn`` takes a return value and returns it when the function is
    called (similar to defining a simple lambda, but better specifying the
    intent).

  These are set with an ``op=`` argument, instead of a ``call_fake=``. For
  example:

  .. code-block:: python

     spy_on(pen.emit_poison, op=kgb.SpyOpRaise(PoisonEmptyError()))

  Or, for one of the more complex examples:

  .. code-block:: python

     spy_on(traps.trigger, op=kgb.SpyOpMatchAny([
         {
             'args': ('hallway_lasers',),
             'call_fake': _send_wolves,
         },
         {
             'args': ('trap_tile',),
             'call_fake': _spill_hot_oil,
         },
         {
             'args': ('infrared_camera',),
             'kwargs': {
                 'sector': 'underground_passage',
             },
             'call_original': False,
         },
     ]))

* Added an ``assertSpyNotCalledWith()`` assertion method.

  Like the name suggests, it asserts that a spy has not been called with
  the provided arguments. It's the inverse of ``assertSpyCalledWith()``.

* ``SpyAgency``'s assertion methods can now be used even without mixing it
  into a ``TestCase``.

* Fixed a crash in ``SpyAgency.unspy_all()``.

* Fixed the grammar in an error message about slippery functions.


kgb 5.0 (10-April-2020)
=======================

* Added support for Python 3.8.

  Functions with positional-only arguments on Python 3.8 will now work
  correctly, and the positional-only arguments will factor into any spy
  matching.

* Added several new unit test assertion methods:

  * ``assertHasSpy``
  * ``assertSpyCalled``
  * ``assertSpyNotCalled``
  * ``assertSpyCallCount``
  * ``assertSpyCalledWith``
  * ``assertSpyLastCalledWith``
  * ``assertSpyReturned``
  * ``assertSpyLastReturned``
  * ``assertSpyRaised``
  * ``assertSpyLastRaised``
  * ``assertSpyRaisedMessage``
  * ``assertSpyLastRaisedMessage``

  We recommend using these for unit tests instead of checking individual
  properties of calls, as they'll provide better output and help you find out
  why spies have gone rogue.

* Added support for spying on "slippery" functions.

  A slippery function is defined (by us) as a function on an object that is
  actually a different function every time you access it. In other words, if
  you were to just reference a slippery function as an attribute two times,
  you'd end up with two separate copies of that function, each with their own
  ID.

  This can happen if the "function" is actually some decorator that returns a
  new function every time it's accessed. A real-world example would be the
  Python Stripe module's API functions, like ``stripe.Customer.delete``.

  In previous versions of kgb, you wouldn't be able to spy on these
  functions. With 5.0, you can spy on them just fine by passing
  ``owner=<instance>`` when setting up the spy:

  .. code-block:: python

     spy_on(myobj.slippery_func,
            owner=myobj)

* Lots of internal changes to help keep the codebase organized and
  manageable, as Python support increases.


kgb 4.0 (30-July-2019)
======================

* Added ``call_original()``, which calls the original spied-on function.

  The call will not be logged, and will invoke the original behavior of
  the function. This is useful when a spy simply needs to wrap another
  function.

* Updated the Python 3 support to use the modern, non-deprecated support
  for inspecting and formatting function/method signatures.


kgb 3.0 (23-March-2019)
=======================

* Added an argument to ``spy_on()`` for specifying an explicit owner class
  for unbound methods, and warn if missing.

  Python 3.x doesn't have a real way of determining the owning class for
  unbound methods, and attempting to spy on an unbound method can end up
  causing a number of problems, potentially interfering with spies that
  are a subclass or superclass of the spied object.

  ``spy_on()`` now accepts an ``owner=`` parameter for unbound methods in
  order to explicitly specify the class. It will warn if this is missing,
  providing details on what it thinks the owner is and the recommended
  changes to make to the call.

* Fixed spying on unbound methods originally defined on the parent class
  of a specified or determined owning class.

* Fixed spying on old-syle classes (those not inheriting from ``object``)
  on Python 2.6 and early versions of 2.7.


kgb 2.0.3 (18-August-2018)
==========================

* Added a version classifier for Python 3.7.

* Fixed a regression on Python 2.6.


kgb 2.0.2 (9-July-2018)
=======================

* Fixed spying on instances of classes with a custom ``__setattr__``.

* Fixed spying on classmethods defined in the parent of a class.


kgb 2.0.1 (12-March-2018)
=========================

* Fixed a regression in spying on classmethods.

* Fixed copying function annotations and keyword-only defaults in Python 3.

* Fixed problems executing some types of functions on Python 3.6.


kgb 2.0 (5-February-2018)
=========================

* Added compatibility with Python 3.6.

* Spy methods for standard functions no longer need to be accessed like:

  .. code-block:: python

	      func.spy.last_call

  Now you can call them the same way you could with methods:

  .. code-block:: python

	      func.last_call

* The ``args`` and ``kwargs`` information recorded for a spy now correspond to
  the function signature and not the way the function was called.

* ``called_with()`` now allows providing keyword arguments to check positional
  arguments by name.

* When spying on a function fails for some reason, the error output is a
  lot more helpful.


kgb 1.1 (5-December-2017)
=========================

* Added ``returned()``, ``last_returned()``, ``raised()``, ``last_raised()``,
  ``raised_with_message()``, and ``last_raised_with_message()`` methods to
  function spies.

  See the README for how this works.

* Added ``called_with()``, ``returned()``, ``raised()``, and
  ``raised_with_message()`` to the individual ``SpyCall`` objects.

  These are accessed through ``spy.calls``, and allow for more conveniently
  checking the results of specific calls in tests.

* ``called_with()`` and ``last_called_with()`` now accept matching subsets of
  arguments.

  Any number of leading positional arguments and any subset of keyword
  arguments can be specified. Prior to 1.0, subsets of keyword arguments
  were supported, but 1.0 temporarily made this more strict.

  This is helpful when testing function calls containing many default
  arguments or when the function takes ``*args`` and ``**kwargs``.


kgb 1.0 (31-October-2017)
=========================

* Added support for Python 3, including keyword-only arguments.

* Function signatures for spies now mimic that of the spied-on functions,
  allowing Python's ``getargspec()`` to work.


kgb 0.5.3 (28-November-2015)
============================

* Objects that evaluate to false (such as objects inheriting from ``dict``)
  can now be spied upon.


kgb 0.5.2 (17-March-2015)
=========================

* Expose the spy when using ``spy_on`` as a context manager.

  Patch by Todd Wolfson.


kgb 0.5.1 (2-June-2014)
=======================

* Added support for spying on unbound member functions on classes.


kgb 0.5.0 (23-May-2013)
=======================

* First public release.

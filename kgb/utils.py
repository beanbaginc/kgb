"""Common utility functions used by kgb."""

from __future__ import unicode_literals

import inspect
from unittest.util import safe_repr

from kgb.pycompat import iteritems


def get_defined_attr_value(owner, name, ancestors_only=False):
    """Return a value as defined in a class, instance, or ancestor.

    This will look for the real definition, and not the definition returned
    when accessing the attribute or instantiating a class. This will bypass any
    descriptors and return the actual definition from the instance or class
    that defines it.

    Args:
        owner (type or object):
            The owner of the attribute.

        name (unicode):
            The name of the attribute.

        ancestors_only (bool, optional):
            Whether to only look in ancestors of ``owner``, and not in
            ``owner`` itself.

    Returns:
        object:
        The attribute value.

    Raises:
        AttributeError:
            The attribute could not be found.
    """
    if not ancestors_only:
        d = owner.__dict__

        if name in d:
            return d[name]

    if not inspect.isclass(owner):
        # NOTE: It's important we use __class__ and not type(). They are not
        #       synonymous. The latter will not return the class for an
        #       instance for old-style classes.
        return get_defined_attr_value(owner.__class__, name)

    for parent_cls in owner.__bases__:
        try:
            return get_defined_attr_value(parent_cls, name)
        except AttributeError:
            pass

    raise AttributeError


def is_attr_defined_on_ancestor(cls, name):
    """Return whether an attribute is defined on an ancestor of a class.

    Args:
        name (unicode):
            The name of the attribute.

    Returns:
        bool:
        ``True`` if an ancestor defined the attribute. ``False`` if it did not.
    """
    try:
        get_defined_attr_value(cls, name, ancestors_only=True)
        return True
    except AttributeError:
        return False


def format_spy_kwargs(kwargs):
    """Format keyword arguments.

    This will convert all keys to native strings, to help with showing
    more reasonable output that's consistent. The keys will also be
    provided in sorted order.

    Args:
        kwargs (dict):
            The dictionary of keyword arguments.

    Returns:
        unicode:
        The formatted string representation.
    """
    return '{%s}' % ', '.join(
        '%s: %s' % (safe_repr(str(key)), safe_repr(value))
        for key, value in sorted(iteritems(kwargs),
                                 key=lambda pair: pair[0])
    )

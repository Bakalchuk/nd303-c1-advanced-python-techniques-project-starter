"""Provide filters for querying close approaches and limit the generated results.

The `create_filters` function produces a collection of objects that is used by
the `query` method to generate a stream of `CloseApproach` objects that match
all of the desired criteria. The arguments to `create_filters` are provided by
the main module and originate from the user's command-line options.

This function can be thought to return a collection of instances of subclasses
of `AttributeFilter` - a 1-argument callable (on a `CloseApproach`) constructed
from a comparator (from the `operator` module), a reference value, and a class
method `get` that subclasses can override to fetch an attribute of interest from
the supplied `CloseApproach`.

The `limit` function simply limits the maximum number of values produced by an
iterator.

"""
import operator
from itertools import islice


class UnsupportedCriterionError(NotImplementedError):
    """A filter criterion is unsupported."""


class AttributeFilter:
    """A general superclass for filters on comparable attributes.

    An `AttributeFilter` represents the search criteria pattern comparing some
    attribute of a close approach (or its attached NEO) to a reference value. It
    essentially functions as a callable predicate for whether a `CloseApproach`
    object satisfies the encoded criterion.

    It is constructed with a comparator operator and a reference value, and
    calling the filter (with __call__) executes `get(approach) OP value` (in
    infix notation).

    Concrete subclasses can override the `get` classmethod to provide custom
    behavior to fetch a desired attribute from the given `CloseApproach`.
    """

    def __init__(self, op, value):
        """Construct a new `AttributeFilter` from an binary predicate and a reference value.

        The reference value will be supplied as the second (right-hand side)
        argument to the operator function. For example, an `AttributeFilter`
        with `op=operator.le` and `value=10` will, when called on an approach,
        evaluate `some_attribute <= 10`.

        :param op: A 2-argument predicate comparator (such as `operator.le`).
        :param value: The reference value to compare against.
        """
        self.op = op
        self.value = value

    def __call__(self, approach):
        """Invoke `self(approach)`."""
        return self.op(self.get(approach), self.value)

    @classmethod
    def get(cls, approach):
        """Get an attribute of interest from a close approach.

        Concrete subclasses must override this method to get an attribute of
        interest from the supplied `CloseApproach`.

        :param approach: A `CloseApproach` on which to evaluate this filter.
        :return: The value of an attribute of interest, comparable to `self.value` via `self.op`.
        """
        raise UnsupportedCriterionError

    def __repr__(self):
        """Get machine representation of the object."""
        return f"{self.__class__.__name__}(op=operator.{self.op.__name__}, value={self.value})"


class HazardousFilter(AttributeFilter):
    """Filter for querying NEOs by whether they are hazardous."""

    def __init__(self, hazardous):
        """Check hazardous equality."""
        super().__init__(operator.eq, hazardous)

    @classmethod
    def get(cls, approach):
        """Get hazardous field."""
        return approach.neo.hazardous


class DateFilter(AttributeFilter):
    """Filter for querying approaches by exact date."""

    def __init__(self, date):
        """Check for date equality."""
        super().__init__(operator.eq, date)

    @classmethod
    def get(cls, approach):
        """Get the date of the approach."""
        return approach.time.date()


class StartDateFilter(AttributeFilter):
    """Filter for querying approaches by whether they are since specific date."""

    def __init__(self, date):
        """Check if approach's date >= date."""
        super().__init__(operator.ge, date)

    @classmethod
    def get(cls, approach):
        """Get the date of the approach."""
        return approach.time.date()


class EndDateFilter(AttributeFilter):
    """Filter for querying approaches by whether they are before specific date."""

    def __init__(self, date):
        """Check if approach's date <= date."""
        super().__init__(operator.le, date)

    @classmethod
    def get(cls, approach):
        """Get the date of the approach."""
        return approach.time.date()


class MinDistanceFilter(AttributeFilter):
    """Filter for querying approaches by whether they above certain distance."""

    def __init__(self, val):
        """Check if approach's distance >= val."""
        super().__init__(operator.ge, val)

    @classmethod
    def get(cls, approach):
        """Get the distance of the approach."""
        return approach.distance


class MaxDistanceFilter(AttributeFilter):
    """Filter for querying approaches by whether they below certain distance."""

    def __init__(self, val):
        """Check if approach's distance <= val."""
        super().__init__(operator.le, val)

    @classmethod
    def get(cls, approach):
        """Get the distance of the approach."""
        return approach.distance


class MinVelocityFilter(AttributeFilter):
    """Filter for querying approaches by whether they above certain velocity."""

    def __init__(self, val):
        """Check if approach's velocity <= val."""
        super().__init__(operator.ge, val)

    @classmethod
    def get(cls, approach):
        """Get the velocity of the approach."""
        return approach.velocity


class MaxVelocityFilter(AttributeFilter):
    """Filter for querying approaches by whether they below certain velocity."""

    def __init__(self, val):
        """Check if approach's velocity >= val."""
        super().__init__(operator.le, val)

    @classmethod
    def get(cls, approach):
        """Get the velocity of the approach."""
        return approach.velocity


class MinDiameterFilter(AttributeFilter):
    """Filter for querying NEOs by whether they above certain diameter."""

    def __init__(self, val):
        """Check if NEO's diameter >= val."""
        super().__init__(operator.ge, val)

    @classmethod
    def get(cls, approach):
        """Get the diameter of the NEO."""
        return approach.neo.diameter


class MaxDiameterFilter(AttributeFilter):
    """Filter for querying NEOs by whether they below certain diameter."""

    def __init__(self, val):
        """Check if NEO's diameter <= val."""
        super().__init__(operator.le, val)

    @classmethod
    def get(cls, approach):
        """Get the diameter of the NEO."""
        return approach.neo.diameter


def create_filters(date=None, start_date=None, end_date=None,
                   distance_min=None, distance_max=None,
                   velocity_min=None, velocity_max=None,
                   diameter_min=None, diameter_max=None,
                   hazardous=None):
    """Create a collection of filters from user-specified criteria.

    Each of these arguments is provided by the main module with a value from the
    user's options at the command line. Each one corresponds to a different type
    of filter. For example, the `--date` option corresponds to the `date`
    argument, and represents a filter that selects close approaches that occured
    on exactly that given date. Similarly, the `--min-distance` option
    corresponds to the `distance_min` argument, and represents a filter that
    selects close approaches whose nominal approach distance is at least that
    far away from Earth. Each option is `None` if not specified at the command
    line (in particular, this means that the `--not-hazardous` flag results in
    `hazardous=False`, not to be confused with `hazardous=None`).

    The return value must be compatible with the `query` method of `NEODatabase`
    because the main module directly passes this result to that method. For now,
    this can be thought of as a collection of `AttributeFilter`s.

    :param date: A `date` on which a matching `CloseApproach` occurs.
    :param start_date: A `date` on or after which a matching `CloseApproach` occurs.
    :param end_date: A `date` on or before which a matching `CloseApproach` occurs.
    :param distance_min: A minimum nominal approach distance for a matching `CloseApproach`.
    :param distance_max: A maximum nominal approach distance for a matching `CloseApproach`.
    :param velocity_min: A minimum relative approach velocity for a matching `CloseApproach`.
    :param velocity_max: A maximum relative approach velocity for a matching `CloseApproach`.
    :param diameter_min: A minimum diameter of the NEO of a matching `CloseApproach`.
    :param diameter_max: A maximum diameter of the NEO of a matching `CloseApproach`.
    :param hazardous: Whether the NEO of a matching `CloseApproach` is potentially hazardous.
    :return: A collection of filters for use with `query`.
    """
    filters = []
    if date:
        filters.append(DateFilter(date))
    if start_date:
        filters.append(StartDateFilter(start_date))
    if end_date:
        filters.append(EndDateFilter(end_date))
    if distance_min:
        filters.append(MinDistanceFilter(distance_min))
    if distance_max:
        filters.append(MaxDistanceFilter(distance_max))
    if velocity_min:
        filters.append(MinVelocityFilter(velocity_min))
    if velocity_max:
        filters.append(MaxVelocityFilter(velocity_max))
    if diameter_min:
        filters.append(MinDiameterFilter(diameter_min))
    if diameter_max:
        filters.append(MaxDiameterFilter(diameter_max))
    if hazardous is not None:
        filters.append(HazardousFilter(hazardous))

    return filters


def limit(iterator, n=None):
    """Produce a limited stream of values from an iterator.

    If `n` is 0 or None, don't limit the iterator at all.

    :param iterator: An iterator of values.
    :param n: The maximum number of values to produce.
    :yield: The first (at most) `n` values from the iterator.
    """
    if n and n > 0:
        return islice(iterator, n)

    return iterator

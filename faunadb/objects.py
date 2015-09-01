"""
Types used in queries and responses.
See https://faunadb.com/documentation#queries-values-special_types.
"""

from .errors import InvalidQuery
from . import query

class Ref(object):
  """
  FaunaDB ref. See https://faunadb.com/documentation#queries-values.

  A simple wrapper around a string which can be extracted using :samp:`ref.value`.
  Queries that require a Ref will not work if you just pass in a string.
  """

  def __init__(self, class_name, instance_id=None):
    """
    Create a Ref from a string, such as :samp:`Ref("databases/prydain")`.
    Can also call :samp:`Ref("databases", "prydain")` or :samp:`Ref(Ref("databases"), "prydain")`.
    """
    if instance_id is None:
      self.value = class_name
    else:
      self.value = "%s/%s" % (str(class_name), instance_id)

  def to_class(self):
    """
    Gets the class part out of the Ref.
    This is done by removing ref.id().
    So `Ref("a", "b/c").to_class()` will be `Ref("a/b")`.
    """
    return Ref("/".join(self.value.split("/")[0:-1]))

  def id(self):
    """
    Removes the class part of the ref, leaving only the id.
    This is everything after the last `/`.
    """
    return self.value.split("/")[-1]

  def to_fauna_json(self):
    """Wraps it in a @ref hash to be sent as a query."""
    return {"@ref": self.value}

  def __str__(self):
    return self.value

  def __repr__(self):
    return "Ref(%s)" % repr(self.value)

  def __eq__(self, other):
    return isinstance(other, Ref) and self.value == other.value

  def __ne__(self, other):
    return not self == other


class Set(object):
  """
  FaunaDB Set match. See https://faunadb.com/documentation#queries-sets.
  For constructing sets out of other sets, see set functions in faunadb.query.
  """

  @staticmethod
  def match(match, index):
    """See https://faunadb.com/documentation#queries-sets."""
    return Set({"match": match, "index": index})

  @staticmethod
  def union(*sets):
    """See https://faunadb.com/documentation#queries-sets."""
    return Set({"union": sets})

  @staticmethod
  def intersection(*sets):
    """See https://faunadb.com/documentation#queries-sets."""
    return Set({"intersection": sets})

  @staticmethod
  def difference(*sets):
    """See https://faunadb.com/documentation#queries-sets."""
    return Set({"difference": sets})

  @staticmethod
  def join(source, target):
    """See https://faunadb.com/documentation#queries-sets."""
    return Set({"join": source, "with": target})

  def __init__(self, query_json):
    self.query_json = query_json

  def to_fauna_json(self):
    # pylint: disable=missing-docstring
    return {"@set": self.query_json}

  def iterator(self, client, page_size=None):
    """
    Iterator that keeps getting new pages of a set.
    :param page_size:
      Number of instances to be fetched at a time.
    :return:
      Iterator through all elements in the set.
    """

    def get_page(**kwargs):
      return Page.from_json(client.query(query.paginate(self, **kwargs)).resource)

    page = get_page(size=page_size)
    for val in page.data:
      yield val

    next_cursor = "after" if page.after is not None else "before"

    while getattr(page, next_cursor) is not None:
      page = get_page(**{"size": page_size, next_cursor: getattr(page, next_cursor)})
      for val in page.data:
        yield val

  def __repr__(self):
    return "Set(%s)" % repr(self.query_json)

  def __eq__(self, other):
    return isinstance(other, Set) and self.query_json == other.query_json

  def __ne__(self, other):
    return not self == other


class Event(object):
  """FaunaDB Event. See https://faunadb.com/documentation#queries-values."""

  @staticmethod
  def from_json(json):
    """
    Events are not automatically converted.
    Use Event.from_json on a dict that you know represents an Event.
    """
    return Event(json["ts"], json["action"], json["resource"])

  # pylint: disable=invalid-name
  def __init__(self, ts, action=None, resource=None):
    self.ts = ts
    "Microsecond UNIX timestamp at which the event occurred."
    if action not in (None, "create", "delete"):
      raise InvalidQuery("Action must be create or delete or None.")
    self.action = action
    """"create" or "delete"""""
    self.resource = resource
    "The Ref of the affected instance."

  def to_fauna_json(self):
    # pylint: disable=missing-docstring
    dct = {"ts": self.ts, "action": self.action, "resource": self.resource}
    return {k: v for k, v in dct.iteritems() if v is not None}

  def __repr__(self):
    return "Event(ts=%s, action=%s, resource=%s)" % (
      repr(self.ts), repr(self.action), repr(self.resource))

  def __eq__(self, other):
    return isinstance(other, Event) and \
      self.ts == other.ts and \
      self.action == other.action and \
      self.resource == other.resource

  def __ne__(self, other):
    return not self == other


class Page(object):
  """
  A single pagination result.
  See :samp:`paginate` in the `docs <https://faunadb.com/documentation#queries-read_functions>`__.
  """

  @staticmethod
  def from_json(json):
    return Page(json["data"], json.get("before"), json.get("after"))

  def __init__(self, data, before=None, after=None):
    self.data = data
    """
    Always a list.
    Elements could be raw data; some methods (such as :doc:`model` :py:meth:`list`) convert data.
    """
    self.before = before
    """Optional :any:`Ref` for an instance that comes before this page."""
    self.after = after
    """Optional :any:`Ref` for an instance that comes after this page."""

  def map_data(self, func):
    return Page([func(x) for x in self.data], self.before, self.after)

  def __repr__(self):
    return "Page(data=%s, before=%s, after=%s)" % (self.data, self.before, self.after)

  def __eq__(self, other):
    return isinstance(other, Page) and\
      self.data == other.data and\
      self.before == other.before and\
      self.after == other.after

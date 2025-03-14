import pytest
from bluesky.tests.conftest import RE  # noqa
from ophyd.tests.conftest import hw  # noqa
from suitcase.utils.tests.conftest import (  # noqa
    plan_type,
    detector_list,
    event_type,
)  # noqa


@pytest.fixture()
def generate_data(RE, detector_list, event_type):  # noqa
    """A fixture that returns event data for a number of test cases.

    Returns a list of (name, doc) tuples for the plan passed in as an arg.

    Parameters
    ----------
    RE : object
        pytest fixture object imported from `bluesky.test.conftest`
    detector_list : list
        pytest fixture defined in `suitcase.utils.conftest` which returns a
        list of detectors
    event_type : list
        pytest fixture defined in `suitcase.utils.conftest` which returns a
        list of 'event_types'.
    """

    def _generate_data_func(plan, ignore=None):
        """Generates data to be used for testing of suitcase.*.export(..)
        functions

        Parameters
        ----------
        plan : the plan to use to generate the test data

        Returns
        -------
        collector : list
            A list of (name, doc) tuple pairs generated by the run engine.
        ignore : list, optional
            list of the pytest.fixture parameter 'values' to ignore.
        """
        if ignore is None:
            ignore = []

        # define the output lists and an internal list.
        collector = []
        event_list = []

        # define the collector function depending on the event_type
        if event_type(ignore) == "event":

            def collect(name, doc):
                collector.append((name, doc))
                if name == "event":
                    event_list.append(doc)

        elif event_type(ignore) == "event_page":

            def collect(name, doc):
                if name == "event":
                    event_list.append(doc)
                elif name == "stop":
                    collector.append(
                        ("event_page", event_model.pack_event_page(*event_list))
                    )
                    collector.append((name, doc))
                else:
                    collector.append((name, doc))

        elif event_type(ignore) == "bulk_events":

            def collect(name, doc):
                if name == "event":
                    event_list.append(doc)
                elif name == "stop":
                    collector.append(("bulk_events", {"primary": event_list}))
                    collector.append((name, doc))
                else:
                    collector.append((name, doc))

        else:
            raise UnknownEventType(
                "Unknown event_type kwarg passed to " "suitcase.utils.events_data"
            )

        # collect the documents
        RE.subscribe(collect)
        RE(plan(detector_list(ignore)))

        return collector

    return _generate_data_func


@pytest.fixture
def example_data(generate_data, plan_type):
    """A fixture that returns event data for a number of test cases.

    Returns a function that returns a list of (name, doc) tuples for each of
    the plans in plan_type.

    .. note::

        It is recommended that you use this fixture for testing of
        ``suitcase-*`` export functions, for an example see
        ``suitcase-tiff.tests``. This will mean that future additions to the
        test suite here will be automatically applied to all ``suitcase-*``
        repos. Some important implementation notes:

        1. These fixtures are imported into other suitcase libraries via those
        libraries' ``conftest.py`` file. This is automatically set up by
        suitcases-cookiecutter, and no additional action is required.

        2. If any of the parameters from the fixtures above are not valid for
        the suitcase you are designing and cause testing issues please skip
        them internally by adding them to the ``ignore`` kwarg list via the
        line ``collector = example_data(ignore=[param_to_ignore, ...])``.

    Parameters
    ----------
    generate_data : list
        pytest fixture defined in `suitcase.utils.conftest` which returns a
        function that accepts a plan as an argument and returns name, do pairs
    plan_type : list
        pytest fixture defined in `suitcase.utils.conftest` which returns a
        list of 'plans' to test against.
    """

    def _example_data_func(ignore=[]):
        """returns a list of (name, doc) tuples for a number of test cases

        ignore : list optional
            list of the pytest.fixture parameter 'values' to ignore, this is
            also passed down to `generate_data`
        """

        return generate_data(plan_type(ignore), ignore=ignore)

    return _example_data_func

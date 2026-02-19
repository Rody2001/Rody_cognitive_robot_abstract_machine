Parametrization of Objects
==========================

The ``Parameterizer`` class allows you to convert standard Python objects into a probabilistic representation.
This is achieved by mapping object attributes to random variables and their values to assignments in a ``SimpleEvent``.

The core idea is to use a "template" object where certain fields are marked to be parameterized using the Ellipsis (``...``) or assigned concrete values, while other fields can be excluded using ``None``.

The ``Parameterizer`` first converts the input object into a ``DataAccessObject`` (DAO) and then recursively traverses its attributes and relationships to create a ``Parameterization``.

Basic Usage
-----------

To generate_parameterizations an object, you can pass an instance of a class to the ``generate_parameterizations`` method.
Attributes of the object will be converted into ``ObjectAccessVariable`` instances.

.. code-block:: python

    from krrood.probabilistic_knowledge.parameterizer import Parameterizer
    from dataset.example_classes import Position

    # Parameterize all fields of a Position
    position = Position(..., ..., ...)
    parameterization = Parameterizer().generate_parameterizations(position)

    # The result contains variables for x, y, and z
    for var in parameterization.variables:
        print(var.variable.name)
        # Output: PositionDAO.x, PositionDAO.y, PositionDAO.z

    # Access the corresponding random events variables
    random_vars = parameterization.random_events_variables

Controlling Parameterization
----------------------------

You can control which fields are included and whether they have a fixed value in the resulting ``SimpleEvent``:

- **Ellipsis (``...``)**: Signals that the field should be parameterized as a variable, but its value in the ``SimpleEvent`` remains unconstrained (or "missing").
- **Concrete Value**: If a field has a value (e.g., ``3.14``), it is parameterized as a variable, and the ``SimpleEvent`` will contain the assignment (e.g., ``{variable: 3.14}``).
- **None**: If a field is set to ``None``, it is completely ignored and will not be included in the parameterization.

Example with mixed values:

.. code-block:: python

    from krrood.probabilistic_knowledge.parameterizer import Parameterizer
    from dataset.example_classes import Orientation

    # Parameterize x and z, set y to a fixed value, and skip w
    orientation = Orientation(..., 3.14, ..., None)
    parameterization = Parameterizer().generate_parameterizations(orientation)

    # simple_event will contain the assignment for y
    print(parameterization.simple_event)
    # Output: SimpleEvent({OrientationDAO.y: 3.14})

Nested Objects and Relationships
--------------------------------

The ``Parameterizer`` handles nested objects and relationships automatically. It recursively processes one-to-one and one-to-many relationships.

.. code-block:: python

    from krrood.probabilistic_knowledge.parameterizer import Parameterizer
    from dataset.example_classes import Pose, Position, Orientation

    pose = Pose(
        position=Position(..., ..., ...),
        orientation=Orientation(..., ..., ..., None)
    )

    parameterization = Parameterizer().generate_parameterizations(pose)
    # This creates variables like PoseDAO.position.x and PoseDAO.orientation.x

Probabilistic Models
--------------------

Once you have a ``Parameterization``, you can use it to initialize probabilistic models.
A common starting point is creating a fully factorized distribution over the variables:

.. code-block:: python

    # Create a fully factorized probabilistic circuit (PC)
    pc = parameterization.create_fully_factorized_distribution()

The ``Parameterization`` class
------------------------------

The ``generate_parameterizations`` method returns a ``Parameterization`` object, which acts as a container for:

- ``variables``: A list of ``ObjectAccessVariable`` mapping the object's attributes to random variables.
- ``simple_event``: A ``SimpleEvent`` representing the state of the parameterized object.

Key methods of ``Parameterization``:

- ``random_events_variables``: Returns the underlying ``random_events.variable.Variable`` objects.
- ``fill_missing_variables()``: Ensures the ``simple_event`` covers all variables in the parameterization.
- ``create_fully_factorized_distribution()``: Utility to create a basic ``ProbabilisticCircuit``.
- ``merge_parameterization(other)``: Merges another parameterization into the current one.

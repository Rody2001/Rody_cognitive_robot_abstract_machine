from __future__ import annotations

import typing
from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from typing import Dict, Callable, Type, Optional

from typing_extensions import Any

import random_events.variable
from krrood.adapters.json_serializer import list_like_classes
from krrood.entity_query_language.core.base_expressions import SymbolicExpression
from krrood.entity_query_language.core.mapped_variable import MappedVariable
from krrood.entity_query_language.factories import variable, and_
from krrood.entity_query_language.query.match import UnderspecifiedVariable
from krrood.probabilistic_knowledge.probable_variable import (
    QueryToRandomEventTranslator,
)
from random_events.set import Set
from random_events.variable import variable_from_name_and_type


@dataclass
class CallableAndKwargs:
    """
    A hierarchy of callables and their keyword arguments.
    This behaves like a factory for underspecified method calls where the missing parameters are indicated by Ellipsis.
    """

    callable: Callable
    """
    The callable to call when all parameters are specified.
    """

    kwargs: Dict[str, Any] = field(default_factory=dict)
    """
    The keyword arguments to pass to the callable.
    """

    def __deepcopy__(self, memo):
        return self.__class__(
            self.callable,
            {name: deepcopy(value) for name, value in self.kwargs.items()},
        )

    @cached_property
    def flat_assignments(
        self,
    ) -> Dict[ParametrizationVariable, Any]:
        """
        :return: A dictionary mapping all variables mentioned in the CallableAndKwargs to their values.
        """
        result = {}

        symbolic_access_for_kwargs = variable(self.callable, [])
        symbolic_access_for_where = variable(self.callable, [])
        symbolic_access = ParametrizationVariable(
            variable_in_kwargs=symbolic_access_for_kwargs,
            variable_in_where_conditions=symbolic_access_for_where,
            type_hint=None,
            value=None,
        )

        self._flat_assignments(symbolic_access, result)
        return result

    def get_type_hint_of_keyword_argument(self, name: str):
        hints = typing.get_type_hints(
            self.callable,
            globalns=getattr(self.callable, "__globals__", None),
            localns=None,
            include_extras=True,  # keeps Annotated[...] / other extras if you use them
        )
        return hints.get(name)

    def _flat_assignments(
        self,
        symbolic_access: ParametrizationVariable,
        result: Dict,
    ):
        """
        Recursively extract all variables and their values from the CallableAndKwargs.

        :param symbolic_access: The current symbolic access to the variables.
        :param result: The dictionary to store the extracted variables and their values.
        """
        symbolic_access.variable_in_kwargs = symbolic_access.variable_in_kwargs.kwargs
        for key, value in self.kwargs.items():

            # update access patterns
            current_symbolic_access = symbolic_access.apply_attribute_access(key)
            current_symbolic_access.type_hint = self.get_type_hint_of_keyword_argument(
                key
            )

            if isinstance(value, list_like_classes):
                # handle list like classes by wrapping the index access
                for index, element in enumerate(value):

                    # update access pattern for the current index
                    current_symbolic_access_index = (
                        current_symbolic_access.apply_index_access(index)
                    )
                    current_symbolic_access.type_hint = (
                        self.get_type_hint_of_keyword_argument(key)
                    )  # get the type hint from the signature of the function
                    if isinstance(element, CallableAndKwargs):
                        element._flat_assignments(
                            current_symbolic_access_index,
                            result,
                        )
                    else:
                        current_symbolic_access.is_leaf = True
                        result[current_symbolic_access_index] = element

            elif isinstance(value, CallableAndKwargs):
                value._flat_assignments(
                    current_symbolic_access,
                    result,
                )
            else:
                current_symbolic_access.is_leaf = True
                result[current_symbolic_access] = value

    def apply_assignments(self, bindings: Dict[ParametrizationVariable, Any]):
        """
        Apply the given bindings to the CallableAndKwargs instance.
        This updates the `kwarg` attribute in-place.

        :param bindings: A dictionary mapping symbolic accesses from this instance to their values.
        """
        for variable, value in bindings.items():
            variable.variable_in_kwargs._set_external_instance_value_(self, value)

    def construct_instance(self):
        """
        Construct a python object from the CallableAndKwargs instance.

        ..note:: This method may work with ellipsis, but it's not guaranteed to work with all types.

        :return: The constructed object.
        """
        constructed_kwargs = {}
        for key, value in self.kwargs.items():
            if isinstance(value, list_like_classes):
                constructed_kwargs[key] = type(value)(
                    (
                        element.construct_instance()
                        if isinstance(element, CallableAndKwargs)
                        else element
                    )
                    for element in value
                )

            elif isinstance(value, CallableAndKwargs):
                constructed_kwargs[key] = value.construct_instance()
            else:
                constructed_kwargs[key] = value
        return self.callable(**constructed_kwargs)


@dataclass
class UnderspecifiedToCallableAndKwargsTranslator:
    """
    Extract CallableAndKwargs object from an UnderspecifiedVariable.
    """

    statement: UnderspecifiedVariable
    """
    The UnderspecifiedVariable to translate.
    """

    def translate(self) -> CallableAndKwargs:
        """
        :return: A CallableAndKwargs object extracted from the UnderspecifiedVariable.
        """
        return self._translate(self.statement)

    def _translate(
        self,
        statement: UnderspecifiedVariable,
    ) -> CallableAndKwargs:
        """
        Extract CallableAndKwargs object from an UnderspecifiedVariable recoursively.
        :param statement: The statement to translate.
        :return: A CallableAndKwargs object extracted from the statement.
        """

        current_callable = statement.factory

        kwargs = dict()

        for key, argument in statement.kwargs.items():

            if isinstance(argument, list_like_classes):

                kwargs[key] = type(argument)(
                    (
                        self._translate(element)
                        if isinstance(element, UnderspecifiedVariable)
                        else element
                    )
                    for element in argument
                )

            elif isinstance(argument, UnderspecifiedVariable):
                kwargs[key] = self._translate(argument)

            else:
                kwargs[key] = argument
        return CallableAndKwargs(current_callable, kwargs)


@dataclass
class ParametrizationVariable:
    """
    Grouping of variables that appear in different expressions but mean the same thing.
    """

    variable_in_kwargs: MappedVariable
    """
    The variable in the kwargs of the factory used for constructing the final object.
    This one is guaranteed to appear.
    """

    variable_in_where_conditions: MappedVariable
    """
    The variable in the where conditions. This one is very likely to exist. 
    """

    value: Any = None
    """
    The value this variable has in the Kwargs"""

    type_hint: Optional[Type] = None
    """
    The type hint of the variable extracted from the signature of the factory.
    """

    is_leaf: bool = False
    """
    Whether this variable is a leaf variable.
    A leaf variable is a variable where its value was not an `underspecified` statement.
    """

    def __hash__(self):
        return hash(self.variable_in_kwargs)

    @property
    def name(self) -> str:
        return self.variable_in_where_conditions._name_

    def apply_attribute_access(self, attribute: str):
        """
        Apply attribute access to the EQL variables.
        :param attribute: The namee of the attribute
        :return: A new ParametrizationVariable with the attribute access applied.
        """
        if self.is_leaf:
            raise ValueError("Cannot apply attribute access to leaf variable")
        return self.__class__(
            variable_in_kwargs=self.variable_in_kwargs[attribute],
            variable_in_where_conditions=getattr(
                self.variable_in_where_conditions, attribute
            ),
            value=None,
            type_hint=None,
            is_leaf=False,
        )

    def apply_index_access(self, index: Any):
        """
        Apply index access to the EQL variables.
        :param index: The index to access
        :return: A new ParametrizationVariable with the index access applied.
        """
        if self.is_leaf:
            raise ValueError("Cannot apply index access to leaf variable")
        return self.__class__(
            variable_in_kwargs=self.variable_in_kwargs[index],
            variable_in_where_conditions=self.variable_in_where_conditions[index],
            value=None,
            type_hint=None,
            is_leaf=False,
        )

    @cached_property
    def random_events_variable(self) -> Optional[random_events.variable.Variable]:
        if not self.is_leaf:
            return None

        if isinstance(self.value, SymbolicExpression):
            return random_events.variable.Symbolic(
                self.name,
                Set.from_iterable(self.value.tolist()),
            )

        return variable_from_name_and_type(self.name, self.type_hint)


@dataclass
class Parameters:
    statement: UnderspecifiedVariable

    _factory_compiler: UnderspecifiedToCallableAndKwargsTranslator = field(init=False)
    _random_event_compiler: QueryToRandomEventTranslator = field(init=False)

    def __post_init__(self):
        self._factory_compiler = UnderspecifiedToCallableAndKwargsTranslator(
            self.statement
        )
        self._random_event_compiler = QueryToRandomEventTranslator(
            and_(*self.statement._where_expression)
        )

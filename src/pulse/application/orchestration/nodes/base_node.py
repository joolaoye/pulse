from abc import (
    ABC,
    abstractmethod,
)
from enum import Enum
from time import perf_counter
from typing import (
    ClassVar,
    Dict,
    Generic,
    TypeVar,
    final,
)

from pulse.application.orchestration.logging import NodeLogger

StateT = TypeVar("StateT")
NodeInputT = TypeVar("NodeInputT")
NodeOutputT = TypeVar("NodeOutputT")
StateUpdateT = TypeVar("StateUpdateT")


class BaseNode(
    ABC,
    Generic[
        StateT,
        NodeInputT,
        NodeOutputT,
        StateUpdateT,
    ],
):
    name: ClassVar[str]

    def __init__(
        self,
        node_logger: NodeLogger,
    ) -> None:
        self._node_logger = node_logger

    @final
    async def run(
        self,
        state: StateT,
    ) -> StateUpdateT:
        started_at = perf_counter()

        try:
            input_data = self._read_input(
                state=state,
            )

            self._node_logger.node_started(
                node_name=self.name,
                input_summary=self._summarize_input(
                    input_data=input_data,
                ),
            )

            output_data = await self._execute(
                input_data=input_data,
            )

            state_update = self._build_state_update(
                output_data=output_data,
            )

        except Exception as error:
            elapsed_ms = self._get_elapsed_ms(
                started_at=started_at,
            )

            self._node_logger.node_failed(
                node_name=self.name,
                elapsed_ms=elapsed_ms,
                error=error,
            )

            raise

        elapsed_ms = self._get_elapsed_ms(
            started_at=started_at,
        )

        self._node_logger.node_completed(
            node_name=self.name,
            elapsed_ms=elapsed_ms,
            result_summary=self._summarize_output(
                output_data=output_data,
            ),
        )

        return state_update

    @abstractmethod
    def _read_input(
        self,
        *,
        state: StateT,
    ) -> NodeInputT:
        raise NotImplementedError

    @abstractmethod
    async def _execute(
        self,
        *,
        input_data: NodeInputT,
    ) -> NodeOutputT:
        raise NotImplementedError

    @abstractmethod
    def _build_state_update(
        self,
        *,
        output_data: NodeOutputT,
    ) -> StateUpdateT:
        raise NotImplementedError

    def _summarize_input(
        self,
        *,
        input_data: NodeInputT,
    ) -> Dict[str, object]:
        return {
            "input_type": (input_data.__class__.__name__),
        }

    def _summarize_output(
        self,
        *,
        output_data: NodeOutputT,
    ) -> Dict[str, object]:
        if isinstance(
            output_data,
            Enum,
        ):
            return {
                "value": (output_data.value),
            }

        return {
            "output_type": (output_data.__class__.__name__),
        }

    @staticmethod
    def _get_elapsed_ms(
        *,
        started_at: float,
    ) -> float:
        return (perf_counter() - started_at) * 1_000

    @final
    async def __call__(
        self,
        state: StateT,
    ) -> StateUpdateT:
        return await self.run(
            state=state,
        )

from abc import ABC, abstractmethod
from typing import Any, TypeVar, cast
import logging
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlowData(ABC, BaseModel):
    """
    Base abstract class for all FlowData types.
    Each FlowData type should implement the flow_data_name method to return a unique name for the data type.
    Implements comparison and hashing based on the flow_data_name.
    """
    @staticmethod
    @abstractmethod
    def flow_data_name():
        raise NotImplementedError
    
    def __hash__(self):
        return hash(self.flow_data_name())
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, FlowData):
            return self.flow_data_name() == other.flow_data_name()
        return False


class FlowWorker(ABC):
    """
    Base abstract class for all FlowWorker types.
    Each FlowWorker type should implement the flow_worker_name method to return a unique name for the worker.
    Implements input_data and output_data properties to get the types of input and output data for given worker.
    Each FlowWorker type should implement the run method to perform the actual work.
    """
    @staticmethod
    @abstractmethod
    def flow_worker_name():
        raise NotImplementedError
    
    @property
    def input_data(self):
        return [t for t in self.run.__annotations__.values()][:-1]
    
    @property
    def output_data(self):
        return [t for t in self.run.__annotations__.values()][-1]

    @abstractmethod
    async def run(self, *args):
        raise NotImplementedError

T = TypeVar("T", bound=FlowData)

class Runtime:
    """
    Runtime class to manage the state of the data processing.
    It holds the state of all FlowData types and provides methods to set and get the state.
    It also provides a method to run a FlowWorker, which processes the input data and updates the state.
    The run method takes a FlowWorker instance and runs it with the current state as input.
    The result of the run is used to update current states.
    """
    def __init__(self) -> None:
        self.state: dict[str, FlowData] = {}
        logging.info("Runtime initialized.")

    def set_state(self, data: FlowData):
        self.state[data.flow_data_name()] = data
        logging.info(f"State set: {data.flow_data_name()}")
        logging.info(f"Current states: {self.state}")

    def get_state(self, name: str, _: type[T]) -> T:
        return cast(T, self.state[name])

    async def run(self, worker: FlowWorker):
        logging.info(f"Running {worker.flow_worker_name()}")
        logging.info(f"This worker needs {worker.input_data} input data.")
        args = []

        for input in worker.input_data:
            args.append({t.__class__: t for t in self.state.values()}[input])

        result: set[FlowData] = await worker.run(*args)

        for r in result:
            self.state[r.flow_data_name()] = r

        logging.info(f"Run finished, states: {self.state}")

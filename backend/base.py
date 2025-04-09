from abc import ABC, abstractmethod
from typing import Any, TypeVar, cast
import asyncio
from pydantic import BaseModel


class FlowData(ABC, BaseModel):

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
    def __init__(self) -> None:
        self.state: dict[str, FlowData] = {}
        print("Runtime initialized.")

    def set_state(self, data: FlowData):
        print(f"Setting state {data.flow_data_name()}")
        self.state[data.flow_data_name()] = data

        print('current states:', self.state)

    def get_state(self, name: str, _: type[T]) -> T:
        return cast(T, self.state[name])

    async def run(self, worker: FlowWorker):
        print(f"Running {worker.flow_worker_name()}")
        args = []
        print(f"This worker needs {worker.input_data} input data.") 
        for input in worker.input_data:
            args.append({t.__class__: t for t in self.state.values()}[input])

        result: set[FlowData] = await worker.run(*args)

        for r in result:
            self.state[r.flow_data_name()] = r

        print(f"Run finished, states: {self.state}")


#runtime = Runtime()
#runtime.set_state(TestDataA(4))
#runtime.set_state(TestDataB())
#asyncio.run(runtime.run(TestWorker()))
#print(runtime.state)

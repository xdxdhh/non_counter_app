from base import FlowWorker
from pydantic import BaseModel
import requests
from agents import RunConfig, Runner, Agent, function_tool
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import typing
import asyncio
from prompts import get_data_description_prompt, get_parsing_rules_prompt
from models import PlatformData, DataDescriptionData, FileData, ParserDefinitionData


class Platform(BaseModel):
    # pk, provider, url, providers
    short_name: str
    name: str


class ParserDefinitionAPI(BaseModel):
    parser_name: str
    platforms: typing.List[str]


class PlatformAgentWorker(FlowWorker):
    def __init__(self):
        self.brain_token = "102a5cd33241bd15617ac13d90619b6205a02d8f"

        self.agent = Agent(
            name="Platform Agent",
            handoff_description="Specialist agent for questions about platforms.",
            instructions=f"{RECOMMENDED_PROMPT_PREFIX}"
            "You provide assistance with questions about platforms. User will tell you in which platform is he interested and you goal is to tell him if the platform is available."
            "You can use fetch_all_platforms function that will tell you all the available platforms and also their short names."
            "If the platform is available, your goal is also to tell the user which parsers are capable of processing this platform."
            "To get all the parsers, you can use fetch_all_parsers function. If the platform is not listed between the platforms, it also wont have any parser.",
            model="gpt-4o-mini",
            tools=[self.fetch_all_platforms, self.fetch_all_parsers],
            output_type=PlatformData,
        )

    @function_tool
    async def fetch_all_platforms():
        brain_token = "102a5cd33241bd15617ac13d90619b6205a02d8f"
        url = "https://brain.celus.net/knowledgebase/platforms/"
        headers = {"Authorization": f"Token {brain_token}"}
        print("Fetching all platforms")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        platforms = [Platform.model_validate(p) for p in response.json()]
        return ", ".join(f"{p.name}({p.short_name})" for p in platforms)

    @function_tool
    async def fetch_all_parsers() -> str:
        """Fetch all available parsers from Brain API.
        Returns them in format parser_name(platforms)c
        """
        print("Fetching all parsers")
        brain_token = "102a5cd33241bd15617ac13d90619b6205a02d8f"
        url = "https://brain.celus.net/knowledgebase/parsers/"
        headers = {"Authorization": f"Token {brain_token}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        parsers = [ParserDefinitionAPI.model_validate(p) for p in response.json()]
        # create list of parsers

        return ", ".join(f"Parser {p.parser_name}({p.platforms})" for p in parsers)

    @staticmethod
    def flow_worker_name():
        return "platform_worker"

    async def run(self, platform: PlatformData) -> set[PlatformData]:
        print("Platform Agent: Checking platform", platform.platform_name)
        prompt = f"I am interested in {platform.platform_name} platform."
        config = RunConfig(workflow_name="test_app_1", trace_id="trace_app_1")  # todo
        result = await Runner.run(self.agent, prompt, run_config=config)

        # create the PlayerAgentOutput object
        print("Result of platform agent:")
        print(result.final_output)
        output = PlatformData.model_validate(result.final_output)
        print(output)
        return {output}


class DataDescriptionWorker(FlowWorker):
    def __init__(self):
        self.brain_token = "102a5cd33241bd15617ac13d90619b6205a02d8f"  # todo give metrics and metadata access

        self.agent = Agent(
            name="Data Description Agent",
            handoff_description="Specialist agent for describing data.",
            instructions=get_data_description_prompt(),
            model="gpt-4o",
            # tools=[self.fetch_all_platforms, self.fetch_all_parsers], TODO
            output_type=DataDescriptionData,
        )

    @staticmethod
    def flow_worker_name():
        return "data_description_worker"

    async def run(
        self, file: FileData
    ) -> set[DataDescriptionData]:  # todo will return data description data
        with open(file.filename, "r") as f:
            content = f.read()
            print(content)
            config = RunConfig(
                workflow_name="test_app_1", trace_id="trace_app_description"
            )  # todo
            result = await Runner.run(self.agent, content, run_config=config)
            return {result.final_output}


class ParsingRulesWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Parsing Rules Agent",
            handoff_description="Specialist agent for parsing rules.",
            model="gpt-4o",
            output_type=ParserDefinitionData,
        )

    @staticmethod
    def flow_worker_name():
        return "parsing_rules_worker"

    async def run(
        self, data_description: DataDescriptionData, file: FileData
    ) -> set[ParserDefinitionData]:  # todo output
        with open(file.filename, "r") as f:
            content = f.read()
            metrics = data_description.metrics
            dimensions = data_description.dimensions
            print("Metrics:", metrics)
            print("Dimensions:", dimensions)
            self.agent.instructions = get_parsing_rules_prompt(
                metrics=metrics, dimensions=dimensions
            )

            config = RunConfig(
                workflow_name="test_app_2", trace_id="trace_parsing_rules"
            )  # todo
            # dostane additional data od uzivatele i ten vstupni soubor
            result = await Runner.run(self.agent, content, run_config=config)
            print("Parsing rules generated\n")
            print(result.final_output)

            return {result.final_output}


FLOW_WORKERS: set[type[FlowWorker]] = {
    PlatformAgentWorker,
    DataDescriptionWorker,
    ParsingRulesWorker,
}

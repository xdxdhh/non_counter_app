from base import FlowWorker
from pydantic import BaseModel
import requests
from agents import RunConfig, Runner, Agent, function_tool, RunContextWrapper
import typing
from prompts import (
    get_data_description_prompt,
    get_parsing_rules_prompt,
    get_translation_prompt,
    get_platform_prompt,
)
from models import (
    PlatformData,
    DataDescriptionData,
    FileData,
    ParserDefinitionData,
    ParsedData,
    TranslationData,
)
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import json
from celus_nibbler.definitions import Definition
from celus_nibbler.parsers.dynamic import gen_parser
from celus_nibbler import eat
import pandas as pd
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Platform(BaseModel):
    short_name: str
    name: str


class ParserDefinitionAPI(BaseModel):
    parser_name: str
    platforms: typing.List[str]


class PlatformAgentWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Platform Agent",
            handoff_description="Specialist agent for questions about platforms.",
            instructions=get_platform_prompt(),
            model="gpt-4o-mini",
            tools=[self.fetch_all_platforms, self.fetch_all_parsers],
            output_type=PlatformData,
        )

    @function_tool
    async def fetch_all_platforms() -> str:
        """Fetch all available platforms from Brain API.
            Returns them in format platform_name(short_name)."""
        
        url = "https://brain.celus.net/knowledgebase/platforms/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"} #expects BRAIN_TOKEN in env
        logger.info("Fetching all platforms")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            platforms = [Platform.model_validate(p) for p in response.json()]
            return ",".join(f"{p.name}({p.short_name})" for p in platforms)
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    @function_tool
    async def fetch_all_parsers() -> str:
        """Fetch all available parsers from Brain API.
        Returns them in format parser_name(platforms).
        """
        url = "https://brain.celus.net/knowledgebase/parsers/"
        headers = {"Authorization": f"Token {os.environ.get('BRAIN_TOKEN')}"}
        logger.info("Fetching all parsers")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            parsers = [ParserDefinitionAPI.model_validate(p) for p in response.json()]
            return ",".join(f"Parser {p.parser_name}({p.platforms})" for p in parsers)
        except requests.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    @staticmethod
    def flow_worker_name():
        return "platform_worker"

    async def run(self, platform: PlatformData) -> set[PlatformData]:
        logger.info(f"Platform Agent: Checking platform {platform.platform_name}")
        prompt = f"I am interested in {platform.platform_name} platform."
        result = await Runner.run(self.agent, prompt)
        # create the PlatformData object
        logger.info(f"Platform Agent result: {result.final_output}")
        output = PlatformData.model_validate(result.final_output)
        return {output}


class DataDescriptionWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Data Description Agent",
            handoff_description="Specialist agent for describing data.",
            instructions=get_data_description_prompt(),
            model="gpt-4o",
            output_type=DataDescriptionData,
        )

    @staticmethod
    def flow_worker_name():
        return "data_description_worker"

    async def run(self, file: FileData) -> set[DataDescriptionData]:
        with open(file.filename, "r") as f:
            logger.info("Data Description worker: using file %s", file.filename)
            content = f.read()
            result = await Runner.run(self.agent, content)
            logger.info("Data Description Agent result:")
            logger.info(result.final_output)
            return {result.final_output}


class TranslationWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Translation Agent",
            handoff_description="Agent for metric and dimension translations.",
            instructions=get_translation_prompt(),
            model="gpt-4o-mini",
            output_type=TranslationData,
        )

    @staticmethod
    def flow_worker_name():
        return "translation_worker"

    async def run(self, data_description: DataDescriptionData) -> set[TranslationData]:
        metrics = data_description.metrics
        dimensions = data_description.dimensions
        logger.info("Translation worker: metrics: %s", metrics)
        logger.info("Translation worker: dimensions: %s", dimensions)
        input = f"""Metrics: {metrics},Dimensions: {dimensions}"""
        result = await Runner.run(self.agent, input)
        logger.info("Translation Agent result:")
        logger.info(result.final_output)
        return {result.final_output}


class ParsingRulesWorker(FlowWorker):
    @dataclass
    class Context:
        # necessary for sharing the information to the function tools, which cannot have self argument
        parser_definition: ParserDefinitionData | None = None
        parsed_data: ParsedData | None = None
        filename: str | None = None

    def __init__(self):
        self.agent = Agent[self.Context](
            name="Parsing Rules Agent",
            handoff_description="Specialist agent for parsing rules.",
            model="gpt-4.1",
            tools=[self.check_parsing_rules],
        )
        self.context = self.Context()

    @staticmethod
    def flow_worker_name():
        return "parsing_rules_worker"

    @staticmethod
    def parse_data(string_json_parsing_rules: str, filename: str) -> pd.DataFrame | str:
        """Try to parse the data using the parsing rules."""
        print("Parsing the data into table")
        dict_rules = json.loads(string_json_parsing_rules)
        parser_definition = Definition.parse(dict_rules)

        dynamic_parsers = [gen_parser(parser_definition)]

        print(f"filename: {filename}")
        poops = eat(
            file_path=filename,
            platform="val",
            check_platform=False,
            parsers=[e.name for e in dynamic_parsers],
            dynamic_parsers=dynamic_parsers,
        )

        poops[0].records_with_stats()
        df = pd.DataFrame(poops[0].records())

        # drop item_ids column
        df = df.drop(columns=["item_ids"], errors="ignore")

        # dimension data is dict, divide it into columns
        for col in df.columns:
            if isinstance(df[col].iloc[0], dict):
                # create new columns for each key in the dict
                dict_df = pd.json_normalize(df[col])
                # rename the columns to include the original column name
                dict_df.columns = [f"{col}.{k}" for k in dict_df.columns]
                # concatenate the new columns with the original dataframe
                df = pd.concat([df, dict_df], axis=1)
                # drop the original column
                df = df.drop(columns=[col])

        # keep only non None columns
        df = df.dropna(axis=1, how="all")
        print("finished parsing the data")
        print(df)
        return df

    @staticmethod
    @function_tool
    def check_parsing_rules(
        wrapper: RunContextWrapper[Context], string_json_parsing_rules: str
    ) -> bool | str:
        """Check whether the generated parser rules conform to the expected format."""
        dict_rules = json.loads(string_json_parsing_rules)
        print(dict_rules)
        # validate against parser definiton:
        try:
            ParserDefinitionData.model_validate(dict_rules)
            df = ParsingRulesWorker.parse_data(
                string_json_parsing_rules, filename=wrapper.context.filename
            )
            parsed_data = ParsedData(columns=[], rows=[])
            parsed_data.from_df(df)
            wrapper.context.parsed_data = parsed_data
            wrapper.context.parser_definition = ParserDefinitionData.model_validate(
                dict_rules
            )
        except Exception as e:
            print("Parsing rules are not valid")
            print(e)
            return str(e)

        return True

    async def run(
        self,
        data_description: DataDescriptionData,
        platform: PlatformData,
        file: FileData,
    ) -> set[ParserDefinitionData, ParsedData]:
        metrics = data_description.metrics
        dimensions = data_description.dimensions
        print("Metrics:", metrics)
        print("Dimensions:", dimensions)
        self.agent.instructions = get_parsing_rules_prompt(
            data_description.metrics,
            data_description.dimensions,
            data_description.begin_month_year,
            data_description.end_month_year,
            data_description.title_report,
            data_description.title_identifiers,
            platform.platform_name,
        )
        print("Instructions:", self.agent.instructions)
        with open(file.filename, "r") as f:  # TODO Add additional user data
            self.context.filename = file.filename
            content = f.read()
            config = RunConfig(
                workflow_name="test_6outputs", trace_id="trace_5outputa"
            )  # todo

            await Runner.run(
                self.agent, content, run_config=config, context=self.context
            )
            return {self.context.parser_definition, self.context.parsed_data}


FLOW_WORKERS: set[type[FlowWorker]] = {
    PlatformAgentWorker,
    DataDescriptionWorker,
    ParsingRulesWorker,
    TranslationWorker
}

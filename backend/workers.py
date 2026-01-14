from base import FlowWorker
import requests
from agents import Runner, Agent, function_tool, RunContextWrapper, ModelSettings
import typing
from prompts import (
    get_data_description_prompt,
    get_parsing_rules_prompt,
    get_translation_prompt,
    get_gitlab_prompt,
)
from models import (
    PlatformData,
    DataDescriptionData,
    FileData,
    FileFormat,
    ParserDefinitionData,
    ParsedData,
    TranslationData,
    MetricsDimensionsData,
    UserInfoData,
    BrainMetric,
    BrainDimension,
    BrainPlatform,
    ReportTypeData,
)
from pydantic import BaseModel
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import json
from celus_nibbler.definitions import Definition
from celus_nibbler.parsers.dynamic import gen_parser
from celus_nibbler import eat
import pandas as pd
import logging
from utils.gitlab_client import GitLabClient, Issue
from utils.brain_client import BrainClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataDescriptionWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Data Description Agent",
            handoff_description="Specialist agent for describing data.",
            instructions=get_data_description_prompt(),
            model="gpt-4o",
            output_type=DataDescriptionData,
            tools=[self.fetch_all_metrics, self.fetch_all_dimensions],
        )

    @staticmethod
    def flow_worker_name():
        return "data_description_worker"

    @function_tool
    async def fetch_all_metrics() -> list[BrainMetric]:
        """Fetch all available metrics from Brain API."""
        brain_client = BrainClient()
        return brain_client.get_metrics()

    @function_tool
    async def fetch_all_dimensions() -> list[BrainDimension]:
        """Fetch all available dimensions from Brain API."""
        brain_client = BrainClient()
        return brain_client.get_dimensions()

    async def run(
        self, file: FileData, user_info: UserInfoData
    ) -> set[DataDescriptionData]:
        """
        Generate data description based on the uploaded file and optional user comment.

        The user comment (if provided) is prepended to the file contents so the agent
        can take it into account when describing the data.
        """
        logger.info("Data Description worker: using file %s", file.file_name)
        # Base content from the prepared file (potentially multiple sheets)
        content = file.to_llm_format()

        # If user provided a comment, prepend it to the content sent to the agent
        if user_info.user_comment:
            content = (
                "User comment (additional context to consider):\n"
                f"{user_info.user_comment}\n"
                "\n"
                "------------------------------\n"
                "Data file content to analyze:\n\n"
                f"{content}"
            )

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


class GitlabIssueOutput(BaseModel):
    """Combined output from GitLab issue parsing."""

    platform: PlatformData
    user_info: UserInfoData


class GitlabWorker(FlowWorker):
    def __init__(self):
        self.agent = Agent(
            name="Gitlab Issue Agent",
            handoff_description="Agent for fetching information from Gitlab issue.",
            instructions=get_gitlab_prompt(),
            model="gpt-4o",
            output_type=GitlabIssueOutput,
            tools=[self.fetch_all_platforms],
        )

    @staticmethod
    def flow_worker_name():
        return "gitlab_worker"

    @function_tool
    async def fetch_all_platforms() -> str:
        """Fetch all available platforms from Brain API.
        Returns them in format platform_name(short_name)."""
        brain_client = BrainClient()
        return brain_client.get_platforms()

    async def run(
        self, user_info: UserInfoData
    ) -> set[PlatformData | FileData | UserInfoData]:
        issue_iid = user_info.gitlab_issue
        if issue_iid is None:
            return {
                PlatformData(platform_name="", short_name="", provider=None, url=None)
            }

        # Fetch issue manually
        logger.info(f"Fetching Gitlab issue {issue_iid}")
        client = GitLabClient()
        issue: Issue = client.get_issue(issue_iid)
        client.download_files(
            issue.get_file_paths(), destination_folder="uploaded_files"
        )

        # Prepare content for the agent
        issue_content = issue.model_dump_json()

        # Run agent with issue content directly
        result = await Runner.run(self.agent, issue_content)

        output = GitlabIssueOutput.model_validate(result.final_output)

        platform_output = output.platform
        user_info_output = output.user_info

        file_data = None
        paths = issue.get_file_paths()
        if paths:
            # Take the first file for now-TODO deal with more files(separate issues)
            filename = paths[0].split("/")[-1]
            file_path = os.path.join("uploaded_files", filename)
            if os.path.exists(file_path):
                try:
                    file_format = FileFormat.from_file_extension(filename)
                    file_data = FileData(path=file_path, format=file_format)
                except ValueError:
                    logger.warning(f"Could not determine file format for {filename}")

        if file_data:
            return {platform_output, user_info_output, file_data}
        return {platform_output, user_info_output}


class ParsingRulesWorker(FlowWorker):
    @dataclass
    class Context:
        # necessary for sharing the information to the function tools, which cannot have self argument
        issue_id: int | None = None
        parser_definition: ParserDefinitionData | None = None
        parsed_data: ParsedData | None = None
        file_path: str | None = None
        report_type_id: int | None = None
        parser_id: int | None = None

    def __init__(self):
        self.agent = Agent[self.Context](
            name="Parsing Rules Agent",
            handoff_description="Specialist agent for parsing rules.",
            model="gpt-5.1",
            model_settings=ModelSettings(
                reasoning={"effort": "medium", "summary": "detailed"}
            ),
            tools=[self.check_parsing_rules],
        )
        self.context = self.Context()

    @staticmethod
    def flow_worker_name():
        return "parsing_rules_worker"

    @staticmethod
    def parse_data(string_json_parsing_rules: str, filename: str) -> pd.DataFrame | str:
        """Try to parse the data using the parsing rules."""
        dict_rules = json.loads(string_json_parsing_rules)
        parser_definition = Definition.parse(dict_rules)

        dynamic_parsers = [gen_parser(parser_definition)]

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
        # save the csv into uploaded_files folder
        df.to_csv(
            os.path.join("uploaded_files", f"{filename.split('/')[-1]}_parsed.csv"),
            index=False,
        )
        return df

    @staticmethod
    @function_tool
    def check_parsing_rules(
        wrapper: RunContextWrapper[Context], string_json_parsing_rules: str
    ) -> bool | str:
        """Check whether the generated parser rules conform to the expected format."""
        dict_rules = json.loads(string_json_parsing_rules)
        logger.info(f"Checking parsing rules: {dict_rules}")
        # upload into brain
        brain_client = BrainClient()
        parser_id = brain_client.create_or_update_parser_definition(
            generated_rules=dict_rules,
            report_type_id=wrapper.context.report_type_id,
            parser_id=wrapper.context.parser_id,
            issue_id=wrapper.context.issue_id,
        )
        wrapper.context.parser_id = parser_id
        # validate against parser definiton:
        try:
            ParserDefinitionData.model_validate(dict_rules)
            df = ParsingRulesWorker.parse_data(
                string_json_parsing_rules, filename=wrapper.context.file_path
            )
            parsed_data = ParsedData(columns=[], rows=[])
            parsed_data.from_df(df)
            wrapper.context.parsed_data = parsed_data
            wrapper.context.parser_definition = ParserDefinitionData.model_validate(
                dict_rules
            )
        except Exception as e:
            logger.exception(e)
            return str(e)

        return True

    async def run(
        self,
        data_description: DataDescriptionData,
        platform: PlatformData,
        metrics_dimensions: MetricsDimensionsData,
        file: FileData,
        user_info: UserInfoData,
        report_type: ReportTypeData,
    ) -> set[ParserDefinitionData, ParsedData]:
        metrics_for_llm = [
            (m.data_metric, m.brain_metric.short_name)
            for m in metrics_dimensions.metrics
        ]
        dimensions_for_llm = [
            (d.data_dimension, d.brain_dimension.short_name)
            for d in metrics_dimensions.dimensions
        ]
        self.agent.instructions = get_parsing_rules_prompt(
            metrics_for_llm,
            dimensions_for_llm,
            data_description.begin_month_year,
            data_description.end_month_year,
            data_description.title_report,
            data_description.title_identifiers,
            platform.name,
            user_info.user_comment,
        )
        logger.info("USER COMMENT: %s", user_info.user_comment)
        content = file.to_llm_format()
        self.context.file_path = file.path  # todo name more reasonably
        self.context.report_type_id = report_type.pk
        await Runner.run(self.agent, content, context=self.context)
        return {self.context.parser_definition, self.context.parsed_data}

    async def run_with_progress(
        self,
        data_description: DataDescriptionData,
        platform: PlatformData,
        metrics_dimensions: MetricsDimensionsData,
        file: FileData,
        user_info: UserInfoData,
        report_type: ReportTypeData,
    ):
        """
        Run the worker with progress streaming.
        Yields progress updates as the agent runs.
        """
        metrics_for_llm = [
            (m.data_metric, m.brain_metric.short_name)
            for m in metrics_dimensions.metrics
        ]
        dimensions_for_llm = [
            (d.data_dimension, d.brain_dimension.short_name)
            for d in metrics_dimensions.dimensions
        ]
        self.agent.instructions = get_parsing_rules_prompt(
            metrics_for_llm,
            dimensions_for_llm,
            data_description.begin_month_year,
            data_description.end_month_year,
            data_description.title_report,
            data_description.title_identifiers,
            platform.name,
            user_info.user_comment,
        )
        content = file.to_llm_format()
        self.context.file_path = file.path
        self.context.report_type_id = report_type.pk
        self.context.issue_id = user_info.gitlab_issue
        # Use run_streamed instead of run
        try:
            result = Runner.run_streamed(
                self.agent, content, context=self.context, max_turns=10
            )
        except Exception as e:
            logger.exception(f"Error starting run_streamed: {e}")
            yield {
                "current": 0,
                "total": 10,
                "message": f"Error starting agent: {str(e)}",
                "error": str(e),
                "done": True,
            }
            return

        iteration = 0
        max_iterations = 10

        # Yield initial progress
        yield {
            "current": 0,
            "total": max_iterations,
            "message": "Starting parsing rules generation...",
        }

        try:
            async for event in result.stream_events():
                try:
                    # Skip raw response events (token-by-token updates)
                    if event.type == "raw_response_event":
                        continue

                    # Track tool calls as iterations
                    if event.type == "run_item_stream_event":
                        if event.item.type == "tool_call_item":
                            iteration += 1
                            tool_name = getattr(
                                event.item, "name", "check_parsing_rules"
                            )
                            yield {
                                "current": min(iteration, max_iterations),
                                "total": max_iterations,
                                "message": f"Iteration {iteration}/{max_iterations}: Running {tool_name}...",
                            }
                        elif event.item.type == "tool_call_output_item":
                            yield {
                                "current": min(iteration, max_iterations),
                                "total": max_iterations,
                                "message": f"Iteration {iteration}/{max_iterations}: Tool completed, validating results...",
                            }
                        elif event.item.type == "message_output_item":
                            yield {
                                "current": min(iteration, max_iterations),
                                "total": max_iterations,
                                "message": f"Iteration {iteration}/{max_iterations}: Processing response...",
                            }

                    # When agent updates (handoffs)
                    elif event.type == "agent_updated_stream_event":
                        yield {
                            "current": min(iteration, max_iterations),
                            "total": max_iterations,
                            "message": f"Agent updated: {event.new_agent.name}",
                        }
                except Exception as e:
                    logger.exception(f"Error processing stream event: {e}")
                    yield {
                        "current": min(iteration, max_iterations),
                        "total": max_iterations,
                        "message": f"Error processing event: {str(e)}",
                    }
        except Exception as e:
            logger.exception(f"Error in stream_events: {e}")
            yield {
                "current": min(iteration, max_iterations),
                "total": max_iterations,
                "message": f"Error during streaming: {str(e)}",
                "error": str(e),
                "done": True,
            }
            return

        # Final completion message
        yield {
            "current": max_iterations,
            "total": max_iterations,
            "message": "Complete! Parsing rules generated successfully.",
            "done": True,
        }

        # The context should now have the parser_definition and parsed_data
        # These will be returned and saved by the streaming endpoint


FLOW_WORKERS: set[type[FlowWorker]] = {
    DataDescriptionWorker,
    ParsingRulesWorker,
    TranslationWorker,
    GitlabWorker,
}

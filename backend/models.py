from pydantic import BaseModel
import typing
from enum import Enum
from base import FlowData
import pandas as pd

class Coord(BaseModel):
    """
    Used for data localization.
    Specifies coordinates of the cell in the data.
    """
    row: int
    col: int

class Direction(str, Enum):
    """
    Enumeration for the direction of the data.
    """
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"

class CoordRange(BaseModel):
    """
    Used for data localization.
    Specifies the starting coordinate, direction, and maximum count of cells to be read.
    """
    coord: Coord
    direction: Direction
    max_count: int | None = None

class Value(BaseModel):
    """
    The simplest source - constant value.
    """
    value: typing.Any

Source = typing.Union[Coord, CoordRange, Value]

class TableException(BaseModel):
    class Action(str, Enum):
        """
        Enumeration for the actions to take when a validation error occurs.
        """
        FAIL = "fail"
        SKIP = "skip"
        STOP = "stop"
        PASS = "pass"

class ExtractParams(BaseModel):
    """
    Parameters for extracting data from the source.
    Specifies the details of the extraction process.
    Regex is used to validate the data.
    Default is the default value to be used if no data is found.
    Last value as default specifies if the last value should be used as the default.
    On validation error specifies the action to take if a validation error occurs.
    """
    regex: typing.Pattern | None = None
    default: typing.Any | None = None
    last_value_as_default: bool = False
    on_validation_error: TableException.Action = TableException.Action.FAIL

class RoleEnum(str, Enum):
    """
    Enumeration for the roles of the data sources.
    """
    VALUE = "value"
    DATE = "date"
    TITLE = "title"
    TITLE_ID = "title_id"
    DIMENSION = "dimension"
    METRIC = "metric"
    ORGANIZATION = "organization"

class MetricSource(BaseModel):
    """
    Source for the metric data.
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    """
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.METRIC]

class ComposedDate(BaseModel):
    """
    Stores the composed date information.
    Composed date is a date that is composed of two parts (year and month).
    Each part is a DateSource.
    """
    year: "DateSource"
    month: "DateSource"

class DateSource(BaseModel):
    """
    Source for the date data.
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    Date pattern specifies the format of the date.
    ComposedDate specifies if the date is composed of multiple parts (e.g., year and month).
    """
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    composed: ComposedDate | None = None
    date_pattern: str | None = None
    role: typing.Literal[RoleEnum.DATE]

class DataHeaders(BaseModel):
    """
    Location of the headers in the data, data cells and data direction.
    Data direction is usually perpendicular to the data cells.
    """
    roles: typing.List[typing.Union[MetricSource, DateSource]]
    data_cells: CoordRange
    data_direction: Direction

class TitleSource(BaseModel):
    """
    Source for the title data.
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    """
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.TITLE]

class TitleIdKind(str, Enum):
    """
    Enumeration for the kind of title identifiers used in TitleIdSource.
    """
    ISBN = "ISBN"
    Print_ISSN = "Print_ISSN"
    Online_ISSN = "Online_ISSN"
    Proprietary = "Proprietary"
    DOI = "DOI"
    URI = "URI"

class TitleIdSource(BaseModel):
    """
    Source for the title identifiers data.
    Name specifies the type of identifier (e.g., ISBN, DOI).
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    """
    name: TitleIdKind
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.TITLE_ID]

class OrganizationSource(BaseModel):
    """
    Source for the organization data.
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    """
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.ORGANIZATION]

class DimensionSource(BaseModel):
    """
    Source for the dimension data.
    Name specifies the type of dimension (e.g., author, institution).
    Source specifies the location of the data.
    ExtractParams specifies how to extract the data.
    """
    name: str
    source: Source
    extract_params: ExtractParams | None = ExtractParams()
    role: typing.Literal[RoleEnum.DIMENSION]

class NonCounterGeneric(BaseModel):
    """
    Definition of one data table.
    Includes the headers, metrics, titels, dimensions and organizations.
    """
    metrics: typing.Optional[MetricSource]
    data_headers: DataHeaders
    dates: typing.Optional[DateSource]
    titles: typing.Optional[TitleSource]
    title_ids: typing.List[TitleIdSource] = []
    dimensions: typing.List[DimensionSource] = []
    organizations: typing.Optional[OrganizationSource]
    kind: typing.Literal["non_counter.generic"] = "non_counter.generic"

class Heuristics(BaseModel):
    """
    Heuristics check for the format.
    We currently bypass it by setting the conditions to empty list.
    This Heuristics format is needed for the parser to function correctly.
    """
    conds: typing.List = []
    kind: typing.Literal["and"] = "and"

class DataFormat(BaseModel):
    """
    This DataFormat is needed for the parser to function correctly.
    """
    name: str = "format"

class ParserDefinitionData(FlowData):
    """
    FlowData for storing parser definition information.
    This includes the parser name, data format, platforms,
    metrics to skip, available metrics, and the action to take
    if a metric check fails.
    The parser definition also includes the areas to be parsed,
    metric and dimension aliases, and heuristics.
    """
    parser_name: str
    data_format: DataFormat
    platforms: typing.List[str] = []
    metrics_to_skip: typing.List[str] = []
    available_metrics: typing.Optional[typing.List[str]]
    on_metric_check_failed: TableException.Action = TableException.Action.SKIP
    titles_to_skip: typing.List[str] = []
    areas: typing.List[NonCounterGeneric]
    metric_aliases: typing.List[typing.Tuple[str, str]] = []
    dimension_aliases: typing.List[typing.Tuple[str, str]] = []
    kind: typing.Literal["non_counter.generic"] = "non_counter.generic"
    heuristics: Heuristics = Heuristics()

    @staticmethod
    def flow_data_name():
        return 'parser_definition_data'


class PlatformData(FlowData):
    """
    FlowData for storing platform information.
    This includes the platform name, whether it exists,
    and the names of the parsers associated with the platform.
    """
    platform_name: str
    exists: bool
    parser_names: typing.List[str]

    @staticmethod
    def flow_data_name():
        return 'platform_data'

class UserInfoData(FlowData):
    """
    FlowData for storing any additional information provided by the user.
    """
    user_comment: str

    @staticmethod
    def flow_data_name():
        return 'user_info_data'

class FileData(FlowData):
    """
    FlowData for storing file information.
    This includes the filename of the file to be processed, including its path.
    """
    filename: str

    @staticmethod
    def flow_data_name():
        return 'file_data'
    
class TranslationData(FlowData):
    """
    FlowData for storing translation information.
    This includes the metrics and dimensions translations.
    The translations are represented as lists of strings.
    """
    metrics_translations: typing.List[str]
    dimensions_translations: typing.List[str]

    @staticmethod
    def flow_data_name():
        return 'translation_data'
    
class Granularity(str, Enum):
    """
    Enumeration for the granularity of the data, used in the DataDescriptionData class.
    """
    MONTHLY = "monthly"
    DAILY = "daily"
    OTHER = "other"

class DataDescriptionData(FlowData):
    """
    FlowData for storing data description information.
    This includes the start and end month/year, whether the data is in English,
    whether the report has a title, the granularity of the data,
    the title identifiers, and the metrics and dimensions.
    """
    begin_month_year: str
    end_month_year: str
    english: bool
    title_report: bool
    granularity: Granularity
    title_identifiers : typing.List[TitleIdKind]
    metrics: typing.List[str]
    dimensions: typing.List[str]

    @staticmethod
    def flow_data_name():
        return 'data_description_data'

class ParsedData(FlowData):
    """
    FlowData for storing parsed data.
    This includes the columns and rows of the parsed data.
    The columns are represented as a list of dictionaries,
    where each dictionary contains the field and header for the column.
    The rows are represented as a list of dictionaries,
    where each dictionary contains the data for each row.
    The from_df method converts a pandas DataFrame to the FlowData format.
    """
    columns: list[dict[str,str]]
    rows: list[dict[str,str]]

    def from_df(self, df: pd.DataFrame):
        self.columns = [{"field": col, "header": col} for col in df.columns]
        self.rows = df.to_dict(orient="records")

    @staticmethod
    def flow_data_name():
        return 'parsed_data'
    
FLOW_DATA: set[type[FlowData]] = {PlatformData, FileData, DataDescriptionData, ParserDefinitionData, UserInfoData, ParsedData, TranslationData}


def get_data_description_prompt():
    prompt = """
        You are a data analyst providing assistance to libraries. A librarian will provide you with a CSV file containing usage statistics from a specific platform that they received. Your goal is to describe this file and return the description in a JSON format.
---------------------------------------
This is example output JSON:
  {
        "begin_month_year": "07-21",
        "end_month_year": "06-22",
        "english": 1,
        "granularity": "monthly",
        "title_report": 1,
        "title_identifiers": ["ISBN"],
        "metrics": [
            "Title Playbacks",
            "Views"
        ],
        "dimensions": [
            "Content Provider",
            "Year of Publishing",
            "Platform"
        ],
    },
---------------------------
You are to fill the keys accordingly:
- begin_month_year: The first month and year for which usage statistics are included, in the format MM-YY.
- end_month_year: The last month and year for which usage statistics are included, in the format MM-YY.
- english: 1 if the statistics are in English, 0 if they are in another language.
- granularity: The time granularity of the usage data. Options are: daily, monthly, other.
- title_report: 1 if the report includes granular usage statistics about multiple titles (e.g., books, magazines, audiobooks), or 0 if it only includes summary data (i.e., combined for all titles).
- titles_identifiers: If titles is 1, this should be a list of all identifiers used to define the titles. Choices are: DOI, ISBN, Print_ISSN, Online_ISSN, URI, and Proprietary (for any other identifiers). If there are no identifiers, this should be an empty list.
- metrics: Different usage statistics described in the report, such as Hits, Page Views, or Visitors. Include them exactly as they appear in the report.
- dimensions: Dimensions are additional information for each data record, such as Journal, Platform, Year of Publication, etc. The metrics themselves, titles and title identifiers are not dimensions. Include them exactly as they appear in the report. If there are no additional dimensions this should be an empty list.
------------------

The CSV may contain irrelevant information that is neither metrics nor dimensions. Ignore such fields.
The structure of the CSV may be non-standard; for example, the first row might not be a header.
Please provide the response in JSON format.

"""
    return prompt


def get_parsing_rules_prompt(metrics, dimensions):
    prompt="""
    User will give you text of the CSV he obtained from provider of e-resources usage statistics.
As the CSVs he obtains from different providers are different, he has written universal python parser,  which can parse the data out. For it to work, he needs you to create the parser rules in the correct format.
"""
    prompt += f"""
For start the user will also give you list of metrics, and list of dimensions.
From this csv, you goal is to process the following metrics: {metrics}. So you should locate where this strings are located in the file.
In general, if the metrics names are in one row, they should be placed under 'headers', and if they are not, they should be placed under 'metrics'.
Please consider it carefully. So if you have 'views' and 'issues' metrics, you should find the location of 'views' and 'issues' strings.
And the following dimensions: {dimensions}.
Also extract the dates, they can also be either in the headers key or in the dates key.
"""
    prompt += """
This is documentation regarding the parser format:
##Parsing Rules

###Coordinate Representation
To navigate the files and locate relevant pieces of information, \textbf{Source} model is used.
\textbf{Coordinates} are defined using zero-based indexing, where each coordinate represents a specific row and column in the input file.
A \textbf{Coordinate Range} extends this definition by specifying an ititial cell coordinate and a parsing direction (left, right, up, down).
A Coordinate Range also includes an optional maximum count parameter, which limits the number of row/columns extracted in the specified direction.

Example - this starts at cell (2, 1) and goes right, extracting up to 3 values:

{"coord": { "row": 2, "col": 1 },
"direction": "right",
"max_count": 3}


Each \textbf{Source} of a value within the file is as one of the following:
\begin{itemize}
    \item \textbf{Coordinate} - A single cell in the file.
    \item \textbf{Coordinate Range} - Starting cell and direction for extracting multiple values.
    \item \textbf{Constant value} - A predefined static value, independent of the file content.
\end{itemize}

The source determines the location of specific data within the file, which is then repeatedly used in the parsing rules.

##Extraction Parameters
The \textbf{Extraction Parameters} model provides additional constraints and methods for retrieving data from a given Source. 
These include:
\begin{itemize}
    \item \textbf{default} - Specifies a fallback value to be used when an empty cell is encountered.
    \item \textbf{last\_value\_as\_default} - Uses the last successfully extracted value as the default for empty cells, useful when all values are expected to be identical.
    \item \textbf{regex} - Defines a regular expression pattern to extract specific information from cell content.
    \item \textbf{on\_validation\_error} - Determines the action taken when extraction fails. This parameter can have one of the following values:
    \begin{itemize}
        \item \textbf{fail} - The process stops and reports an error.
        \item \textbf{skip} - The erroneous value is skipped, and processing continues.
        \item \textbf{stop} - The process stops and reports an error.
        \item \textbf{pass} - The invalid value is accepted without error handling.
    \end{itemize}
\end{itemize}

##Content Extractors
The Source and Extraction Parameters are utilized within Content Extractor models, 
each of which specialized in extracting a specific type of data from the file.
Each Extractor model is defined by:
\begin{itemize}
    \item \textbf{Source} indicating the data location.
    \item \textbf{Extraction Parameters}, which define how the data should be retrieved.
    \item \textbf{Role}, specifying the type of information extracted (e.g. dates, metrics).
\end{itemize}

Metrics are extracted using the \textbf{MetricSource} specialized Content Extractor model.
The goal of this extractor is to extract where in the file are the metric names located.
It has the \textbf{source}, \textbf{extract parameters}, and \textbf{role} parameters, with role set to 'metric'.
Organizations are extracted using the \textbf{OrganizationSource} specialized Content Extractor model.
The goal of this extractor is to extract where in the file are the organization names located.
The role is set to 'organization'.
Dimensions has \textbf{source}, \textbf{extract parameters}, and \textbf{role} parameters, with role set to 'dimension'.
It also introduces \textbf{name} parameter, which specifies the extracted dimension.
The goal of the dimensions is to find the values of the dimension of the given name in the file.
Titles are extracted using the \textbf{TitleSource} specialized Content Extractor model.
This model does not introduce any additional parameters beyond the \textbf{source}, \textbf{extract parameters}, and \textbf{role}, which is set to 'title'.

##Dates

Dates are extracted using a specialized Content Extractor model \textbf{DateSource}. 
Like other content extractors, this model is defined by three key components: Source, Extraction Parameters, and a predefined Role, which in this case is set to 'DATE'.
In some cases month and year information is located in separate fields in the file rather than being a single entity.
To accomodate this, the DateSource extractor provides support for composed date extraction. 
This is achieved through the \textbf{composed} parameter, which allows to specify separate sources for the year and month values. 
An example of its usage is shown in Figure \ref{fig:composed_dates}.
This extractor also has optional \textbf{date\_pattern} parameter, which specifies the format of the date in the source, 
which helps parsing non-standard date formats.

This is an example of composed date, with month and year being on different rows:
"composed": {
    "year": {
        "source": {
            "coord": {"row": 0,"col": 5},
            "direction": "right"},
        "role": "date"},
    "month": {
        "source":
            {"coord": {"row": 1,"col": 5},
            "direction": "right"},
        "role": "date"}
}


##Title Identifiers

Title identifiers, such as ISSN, ISBN, and DOI, are handled by the \textbf{TitleIdSource} Content Extractor model.
This model includes a \textbf{name} parameter, which specifies the type of title identifier extracted.
Supported options are ISBN, Print ISSN, Online ISSN, DOI and URI.
Any identifier that does not fit into one of these categories is considered Proprietary.
The role of this extractor is set to 'TITLE\_ID'.


##Data Headers
Data Headers model serves for defining the headers of the data.
Headers may include different data, from dates and metrics to dimensions.
They are again distinguished by the role parameter.

This model is also used to locate the numerical values of the data.
The \textbf{data\_cells} parameter specifies the location of the first data row/column, which are the actual values in the table.
The \textbf{data\_direction} parameter specifies the direction in which the data is organized,
indicating whether the next data will be obtained by going 'down' or 'right' from the data cells.

This is an example of Data Headers model, with date in the headers and the data cells.
The first data cells is in (1,1), the one data is in one row, and data direction is down.

{"roles" : [{
    "source": {"coord": 
        {"row": 0,"col": 1},
        "direction": "right"},
        "role": "date" }],
"data_direction": "down",
"data_cells": {
    "coord": {
        "row": 1,"col": 1},
        "direction": "right"}
}


##Area Definition
Combining all the parsing rules together is Area model.

In general (and this is very important), all the information can either be included in headers, or somewhere else in the file.
When included in the headers, its Content Extractor will be under 'headers'.
When included outside the headers, its Content Extractor will under its specialized field (e.g. metrics, dates, titles, etc.).

Each parser definition file can include multiple areas (multiple tables in one file / sheet).

Each area is defined by:
\begin{itemize}
    \item \textbf{data headers} - DataHeaders model
    \item \textbf{metrics} - optional MetricSource model, used when the metrics are not in the headers
    \item \textbf{dates} - optional DateSource model, used when the dates are not in the headers
    \item \textbf{titles} - optional TitleSource model, used when the titles are not in the headers
    \item \textbf{title ids} - optional list of TitleIdSource models
    \item \textbf{dimensions} - optional list of DimensionSource models, used when the dimensions are not in the headers
    \item \textbf{organizations} - optional list of OrganizationSource models
\end{itemize}

Each information can be localized in either Data Headers (using appropriate roles) or outside the data headers
using the respective fields.
This can be even combined, when for example one part of date is in the headers and the other part is not.

\section{Heuristics}
Second part of each Parser Definition File is Heuristics. For now, keep this empty and return {}.

\section{Metadata}
Metadata include the \textbf{parser\_name}, \textbf{platforms} that the parser can be used for and additional
information for the data processing. This additional information is not neccessarily obtained from the files,
is often obtanied from either historical knowledge or from the customer. You will find it in the user comment if its relevant.
Sometimes multiple platforms share the same or very similar format, so we can use the same parser for multiple platforms.

The \textbf{metric\_aliases} is used when we have previous information that one metric can have several different names 
for this particular platform. It mainly serves to prevent small mismatches such as View/Views/View*.
It defines one resulting name to which all the other names should be mapped.
The \textbf{dimension\_aliases} function in the same manner for information about dimensions.

The \textbf{metrics\_to\_skip} parameter is used when we have previous information that the customer does not want this metric.
It is also used in cases when metrics and dimensions are mixed in the same column or row and we want to skip between them.
The \textbf{titles\_to\_skip} and \textbf{dimensions\_to\_skip} work in the same manner for titles and dimensions.

available metrics - list of all metrics

To summarize, the metadata section contains the following fields:
\begin{itemize}[parsep=0pt, itemsep=0pt, leftmargin=0.5cm]
    \item \textbf{parser name} - The name of the parser, used for identification.
    \item \textbf{platforms} - A list of platforms which can be processed by this parser
    \item \textbf{metrics to skip} - A list of metrics that should be skipped during processing.
    \item \textbf{available metrics} - A list of metrics that are available for processing.
    \item \textbf{titles to skip} - A list of titles that should be skipped during processing.
    \item \textbf{dimensions to skip} - A list of dimensions that should be skipped during processing.
    \item \textbf{metric aliases} - A dictionary of metric aliases.
    \item \textbf{dimension aliases} - A dictionary of dimension aliases.
\end{itemize}

"""

    return prompt
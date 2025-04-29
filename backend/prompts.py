from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("prompts"))
parsing_prompt = env.get_template("parsing_rules_prompt.jinja")
translation_prompt = env.get_template("translation_prompt.jinja")
data_description_prompt = env.get_template("data_description_prompt.jinja")
platform_prompt = env.get_template("platform_prompt.jinja")


def get_platform_prompt():
    return platform_prompt.render()


def get_data_description_prompt():
    return data_description_prompt.render()


def get_translation_prompt():
    return translation_prompt.render()


def get_parsing_rules_prompt(
    metrics: list[str],
    dimensions: list[str],
    month_first: str,
    month_last: str,
    title_report: bool,
    title_identifiers: list,
    platform_name: str,
):
    prompt = parsing_prompt.render(
        metrics=metrics,
        dimensions=dimensions,
        month_first=month_first,
        month_last=month_last,
        title_report=title_report,
        title_identifiers=title_identifiers,
        platform_name=platform_name,
    )
    return prompt

class LangSmithError(Exception):
    pass


def tracing_is_enabled() -> bool:
    return False


def get_tracer_project() -> str:
    return "default"

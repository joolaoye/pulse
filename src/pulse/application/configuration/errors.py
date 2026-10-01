class PodcastShowNotFoundError(
    ValueError,
):
    pass


class PodcastShowAlreadyExistsError(
    ValueError,
):
    pass


class PodcastPipelineNotFoundError(
    ValueError,
):
    pass


class PodcastPipelineAlreadyExistsError(
    ValueError,
):
    pass


class PodcastPipelineScheduleNotFoundError(Exception):
    pass

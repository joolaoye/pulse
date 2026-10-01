class WorkflowRunNotFoundError(
    ValueError,
):
    pass


class WorkflowRunPipelineMismatchError(
    ValueError,
):
    pass


class WorkflowRunFailedError(
    RuntimeError,
):
    def __init__(
        self,
        *,
        run_id: str,
        pipeline_id: str,
        error: Exception,
    ) -> None:
        super().__init__((f"Workflow run '{run_id}' failed for podcast pipeline '{pipeline_id}'."))

        self.run_id = run_id

        self.pipeline_id = pipeline_id

        self.error = error


class NonRetryableWorkflowError(RuntimeError):
    pass


class PodcastPipelineNotFoundError(NonRetryableWorkflowError):
    pass


class PodcastPipelineDisabledError(NonRetryableWorkflowError):
    pass


class MissingCloudResourceError(NonRetryableWorkflowError):
    pass

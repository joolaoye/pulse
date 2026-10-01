class PulseNotInitializedError(RuntimeError):
    pass


class DeploymentPreflightError(RuntimeError):
    pass


class DeploymentBuildError(RuntimeError):
    pass


class DeploymentError(Exception):
    pass

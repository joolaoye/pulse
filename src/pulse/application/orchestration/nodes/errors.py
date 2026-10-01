class MissingNodeInputError(RuntimeError):
    def __init__(
        self,
        *,
        node_name: str,
        input_name: str,
    ) -> None:
        self.node_name = node_name
        self.input_name = input_name

        super().__init__(
            (
                f"Node '{node_name}' requires workflow "
                f"state input '{input_name}', but it "
                "was not present."
            )
        )

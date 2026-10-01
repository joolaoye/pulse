from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class PromptBuilder:
    class ExampleTag(str, Enum):
        GOOD = "good"
        AMBIGUOUS = "ambiguous"

    class FewShotExample(BaseModel):
        tag: "PromptBuilder.ExampleTag"
        user_input: str
        assistant_response: str
        user_feedback: Optional[str] = None

    @staticmethod
    def render_example(example: "PromptBuilder.FewShotExample") -> str:
        tag = example.tag.value

        parts = [
            f"<{tag}_example>",
            "<user_input>",
            example.user_input,
            "</user_input>",
            "<assistant_response>",
            example.assistant_response,
            "</assistant_response>",
        ]

        if example.user_feedback:
            parts.extend(
                [
                    "<user_feedback>",
                    example.user_feedback,
                    "</user_feedback>",
                ]
            )

        parts.append(f"</{tag}_example>")
        return "\n".join(parts)

    @staticmethod
    def render_examples(
        examples: List["PromptBuilder.FewShotExample"],
    ) -> str:
        return "\n\n".join(PromptBuilder.render_example(example) for example in examples)

    @staticmethod
    def inject_examples(base_prompt: str, examples_block: str) -> str:
        return base_prompt.format(examples_block=examples_block)

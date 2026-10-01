from pydantic import BaseModel, Field


class TurnPlanningOutputItem(BaseModel):
    speaker_id: str = Field(
        ...,
        description=(
            "The stable identifier of the available speaker assigned to "
            "perform this conversational turn."
        ),
    )
    conversational_function: str = Field(
        ...,
        description=("The primary conversational move this turn should perform."),
    )
    editorial_objective: str = Field(
        ...,
        description=(
            "The specific idea, question, or listener outcome this turn "
            "should advance without scripting the exact wording."
        ),
    )
    duration_weight: int = Field(
        ...,
        gt=0,
        description=(
            "The relative share of the available section duration that this "
            "turn should receive compared with the other planned turns. "
            "This is a relative planning weight, not a duration in seconds."
        ),
    )

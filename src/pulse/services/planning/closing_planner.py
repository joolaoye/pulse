from pulse.agents import ClosingPlanningAgent, ClosingPlanningInput
from pulse.types import EpisodeBody, EpisodeClosing


class ClosingPlanner:
    def __init__(
        self,
        *,
        closing_planning_agent: ClosingPlanningAgent,
    ) -> None:
        self.closing_planning_agent = closing_planning_agent

    async def plan(
        self,
        *,
        episode_body: EpisodeBody,
        target_duration_seconds: int,
    ) -> EpisodeClosing:
        output = await self.closing_planning_agent.arun(
            ClosingPlanningInput(
                episode_body=episode_body,
                target_duration_seconds=target_duration_seconds,
            )
        )

        return EpisodeClosing(
            target_duration_seconds=target_duration_seconds,
            objective=output.objective,
            resolution_strategy=output.resolution_strategy,
            final_takeaway=output.final_takeaway,
            closing_goal=output.closing_goal,
        )

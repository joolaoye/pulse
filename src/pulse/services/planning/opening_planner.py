from pulse.agents import OpeningPlanningAgent, OpeningPlanningInput
from pulse.types import EpisodeBody, EpisodeOpening


class OpeningPlanner:
    def __init__(
        self,
        *,
        opening_planning_agent: OpeningPlanningAgent,
    ) -> None:
        self.opening_planning_agent = opening_planning_agent

    async def plan(
        self,
        *,
        episode_body: EpisodeBody,
        target_duration_seconds: int,
    ) -> EpisodeOpening:
        output = await self.opening_planning_agent.arun(
            OpeningPlanningInput(
                episode_body=episode_body,
                target_duration_seconds=target_duration_seconds,
            )
        )

        return EpisodeOpening(
            target_duration_seconds=target_duration_seconds,
            objective=output.objective,
            hook_strategy=output.hook_strategy,
            podcast_introduction_goal=output.podcast_introduction_goal,
            speaker_introduction_goal=output.speaker_introduction_goal,
            listener_promise=output.listener_promise,
            transition_goal=output.transition_goal,
        )

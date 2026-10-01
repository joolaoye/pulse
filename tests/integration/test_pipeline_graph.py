from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.base import BaseCheckpointSaver
import pytest

from pulse.application.orchestration.checkpointing import create_sqlite_checkpointer
from pulse.application.orchestration.graph.builder import PulseGraphBuilder
from pulse.application.orchestration.logging.run_logger import RunLogger
from pulse.application.orchestration.nodes import (
    CommitSignalsNode,
    CompleteWithoutEpisodeNode,
    GenerateEpisodeMetadataNode,
    GenerateScriptNode,
    GroupSignalsNode,
    IngestSignalsNode,
    PlanEpisodeNode,
    PostProcessSignalsNode,
    ProcessSemanticsNode,
    ProduceAudioNode,
    PublishEpisodeNode,
    RetrieveSourcesNode,
)
from pulse.application.orchestration.runner.workflow_runner import WorkflowRunner
from pulse.application.orchestration.state import WorkflowState
from pulse.types import (
    Beat,
    BeatTurnPlan,
    BodyTurnPlan,
    ClosingTurnPlan,
    ConversationAngle,
    ConversationQuestion,
    ConversationQuestions,
    Discourse,
    DiscourseType,
    EmbeddedSignal,
    EpisodeBody,
    EpisodeClosing,
    EpisodeMetadata,
    EpisodeOpening,
    EpisodeScript,
    EpisodeTurnTiming,
    NoContentReason,
    OpeningTurnPlan,
    PodcastProfile,
    PodcastShow,
    ProcessedSignal,
    PublicationResult,
    ScriptTurn,
    Segment,
    SegmentTurnPlan,
    Signal,
    SpeakerProfile,
    SpeakerVoiceBinding,
    StoredEpisodeAudio,
    Theme,
    ThemedSignalCluster,
    Turn,
    TurnPlan,
    Tweet,
    WorkflowOutcome,
)

PIPELINE_ID = "pipeline-1"
EPISODE_ID = "episode-1"
SHOW_ID = "show-1"
SIGNAL_ID = "post-1"


def _show() -> PodcastShow:
    return PodcastShow(
        show_id=SHOW_ID,
        title="Pulse",
        description="A show",
        author="Ada",
        website_url="https://pulse.example.com",
        artwork_url="https://cdn.example.com/artwork.png",
        category="Technology",
        language="en-US",
        public_base_url="https://podcasts.example.com",
        feed_object_key="shows/show-1/rss.xml",
    )


def _discourse() -> Discourse:
    tweet = Tweet(id=SIGNAL_ID, text="A new signal.")
    return Discourse(
        discourse_type=DiscourseType.STANDALONE,
        root_tweet=tweet,
        tweets=[tweet],
    )


def _initial_state(run_id: str) -> WorkflowState:
    return WorkflowState(
        run_id=run_id,
        pipeline_id=PIPELINE_ID,
        episode_id=EPISODE_ID,
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        podcast_profile=PodcastProfile(
            name="Pulse",
            purpose="Explain the news",
            target_audience="Builders",
            editorial_style="Direct",
            conversational_style="Curious",
        ),
        speakers=[
            SpeakerProfile(
                speaker_id="host",
                display_name="Ada",
                podcast_role="Host",
                persona="Curious",
                speaking_style="Clear",
            )
        ],
        speaker_voice_bindings=[
            SpeakerVoiceBinding(speaker_id="host", voice_id="voice-1"),
        ],
        target_episode_duration_seconds=300,
        podcast_show=_show(),
        workflow_outcome=None,
        no_content_reason=None,
    )


def _turn_plan() -> TurnPlan:
    turn = Turn(
        speaker_id="host",
        conversational_function="explain",
        editorial_objective="State the point",
        target_duration_seconds=30,
    )
    opening = EpisodeOpening(
        target_duration_seconds=30,
        objective="Open",
        hook_strategy="Hook",
        podcast_introduction_goal="Introduce the show",
        speaker_introduction_goal="Introduce the host",
        listener_promise="A clear explanation",
        transition_goal="Move into the story",
    )
    closing = EpisodeClosing(
        target_duration_seconds=30,
        objective="Close",
        resolution_strategy="Synthesize",
        final_takeaway="Takeaway",
        closing_goal="End",
    )
    beat = Beat(
        primary_signal_id=SIGNAL_ID,
        title="Beat",
        purpose="Explain the signal",
        conversation_angle=ConversationAngle(
            title="Angle",
            perspective="Technology",
            central_thesis="Thesis",
            narrative_hook="Hook",
            listener_value="Value",
            tension="Tension",
        ),
        questions=ConversationQuestions(
            questions=[
                ConversationQuestion(
                    question="Why does this matter?", rationale="It frames the beat."
                ),
            ]
        ),
        target_duration_seconds=60,
    )
    segment = Segment(
        title="Segment",
        narrative_goal="Tell the story",
        target_duration_seconds=60,
        beats=[beat],
    )
    return TurnPlan(
        opening=OpeningTurnPlan(episode_opening=opening, turns=[turn]),
        body=BodyTurnPlan(
            body=EpisodeBody(segments=[segment]),
            segment_turn_plans=[
                SegmentTurnPlan(
                    segment=segment,
                    beat_turn_plans=[BeatTurnPlan(beat=beat, turns=[turn])],
                )
            ],
        ),
        closing=ClosingTurnPlan(episode_closing=closing, turns=[turn]),
    )


def _stored_audio() -> StoredEpisodeAudio:
    return StoredEpisodeAudio(
        object_key=f"shows/{SHOW_ID}/episodes/{EPISODE_ID}/audio.mp3",
        output_format="mp3",
        content_type="audio/mpeg",
        duration_seconds=90.0,
        size_bytes=2048,
        turn_timings=[
            EpisodeTurnTiming(
                script_turn_index=0,
                speaker_id="host",
                start_time_seconds=0.0,
                end_time_seconds=90.0,
            )
        ],
    )


class RecordingPipeline:
    def __init__(
        self,
        *,
        discourses: list[Discourse],
        fail_publications: int = 0,
    ) -> None:
        self.events: list[str] = []
        self.discourses = discourses
        self.fail_publications = fail_publications
        self.publication_calls = 0
        self.published_episode_ids: list[str] = []

    def build_runner(
        self,
        *,
        run_id: str,
        checkpointer: BaseCheckpointSaver,
        log_directory: Path,
    ) -> WorkflowRunner:
        run_logger = RunLogger(
            run_id=run_id,
            pipeline_id=PIPELINE_ID,
            log_directory=log_directory,
        )
        node_logger = run_logger.node_logger
        graph_builder = PulseGraphBuilder(
            retrieve_sources_node=RetrieveSourcesNode(
                node_logger=node_logger,
                x_retriever=cast(Any, self),
                list_id="list-1",
            ),
            ingest_signals_node=IngestSignalsNode(
                node_logger=node_logger,
                ingestor=cast(Any, self),
            ),
            process_semantics_node=ProcessSemanticsNode(
                node_logger=node_logger,
                semantic_processor=cast(Any, self),
            ),
            post_process_signals_node=PostProcessSignalsNode(
                node_logger=node_logger,
                post_processor=cast(Any, self),
            ),
            group_signals_node=GroupSignalsNode(
                node_logger=node_logger,
                signal_group_builder=cast(Any, self),
            ),
            plan_episode_node=PlanEpisodeNode(
                node_logger=node_logger,
                planner=cast(Any, self),
            ),
            generate_script_node=GenerateScriptNode(
                node_logger=node_logger,
                script_generator=cast(Any, self),
            ),
            generate_episode_metadata_node=GenerateEpisodeMetadataNode(
                node_logger=node_logger,
                episode_metadata_generator=cast(Any, self),
            ),
            produce_audio_node=ProduceAudioNode(
                node_logger=node_logger,
                audio_producer=cast(Any, self),
            ),
            publish_episode_node=PublishEpisodeNode(
                node_logger=node_logger,
                podcast_publisher=cast(Any, self),
            ),
            commit_signals_node=CommitSignalsNode(
                node_logger=node_logger,
                signal_committer=cast(Any, self),
            ),
            complete_without_episode_node=CompleteWithoutEpisodeNode(
                node_logger=node_logger,
            ),
        )
        return WorkflowRunner(
            run_id=run_id,
            graph_builder=graph_builder,
            checkpointer=checkpointer,
            run_logger=run_logger,
        )

    async def retrieve(self, *, list_id: str) -> list[Discourse]:
        self.events.append(RetrieveSourcesNode.name)
        assert list_id == "list-1"
        return list(self.discourses)

    async def ingest(self, *, reconstructed_discourses: list[Discourse]) -> list[Signal]:
        self.events.append(IngestSignalsNode.name)
        return [
            Signal(
                id=discourse.root_tweet.id,
                source="x",
                content=discourse.root_tweet.text,
            )
            for discourse in reconstructed_discourses
        ]

    async def process(
        self,
        *,
        signals: list[Signal],
        embedded_signals: list[EmbeddedSignal] | None = None,
    ) -> list[EmbeddedSignal] | list[ProcessedSignal]:
        if embedded_signals is None:
            self.events.append(ProcessSemanticsNode.name)
            return [
                EmbeddedSignal(
                    signal_id=signal.id,
                    embedding=[1.0, 0.0],
                    embedding_version="test",
                )
                for signal in signals
            ]

        self.events.append(PostProcessSignalsNode.name)
        return [
            ProcessedSignal(
                signal_id=signal.id,
                title="Signal",
                markdown_context=signal.content,
                relevance_score=0.9,
                source=signal.source,
            )
            for signal in signals
        ]

    async def build(
        self,
        *,
        embedded_signals: list[EmbeddedSignal],
        processed_signals: list[ProcessedSignal],
    ) -> list[ThemedSignalCluster]:
        del embedded_signals
        self.events.append(GroupSignalsNode.name)
        return [
            ThemedSignalCluster(
                cluster_id=0,
                relevance_score=0.9,
                theme=Theme(title="Theme", summary="Summary"),
                signal_ids=[signal.signal_id for signal in processed_signals],
            )
        ]

    async def plan(self, **_kwargs: Any) -> TurnPlan:
        self.events.append(PlanEpisodeNode.name)
        return _turn_plan()

    async def generate(self, **kwargs: Any) -> EpisodeScript | EpisodeMetadata:
        if "episode_script" in kwargs:
            self.events.append(GenerateEpisodeMetadataNode.name)
            return EpisodeMetadata(title="Episode", description="Description")

        self.events.append(GenerateScriptNode.name)
        return EpisodeScript(
            turns=[ScriptTurn(speaker_id="host", spoken_text="Hello.")],
        )

    async def produce(self, **_kwargs: Any) -> StoredEpisodeAudio:
        self.events.append(ProduceAudioNode.name)
        return _stored_audio()

    async def publish(
        self, *, podcast_show: PodcastShow, publication_request: Any
    ) -> PublicationResult:
        del podcast_show
        self.publication_calls += 1
        self.published_episode_ids.append(publication_request.episode_id)
        self.events.append(PublishEpisodeNode.name)
        if self.publication_calls <= self.fail_publications:
            raise ValueError("publication failed")

        return PublicationResult(
            show_id=publication_request.show_id,
            episode_id=publication_request.episode_id,
            guid=f"urn:pulse:{publication_request.show_id}:{publication_request.episode_id}",
            audio_url="https://podcasts.example.com/shows/show-1/episodes/episode-1/audio.mp3",
            feed_url="https://podcasts.example.com/shows/show-1/rss.xml",
            published_at=publication_request.published_at,
        )

    async def commit(self, **_kwargs: Any) -> None:
        self.events.append(CommitSignalsNode.name)


def _published_events() -> list[str]:
    return [
        RetrieveSourcesNode.name,
        IngestSignalsNode.name,
        ProcessSemanticsNode.name,
        PostProcessSignalsNode.name,
        GroupSignalsNode.name,
        PlanEpisodeNode.name,
        GenerateScriptNode.name,
        GenerateEpisodeMetadataNode.name,
        ProduceAudioNode.name,
        PublishEpisodeNode.name,
        CommitSignalsNode.name,
    ]


@pytest.mark.asyncio
async def test_pipeline_graph_publishes_episode(tmp_path: Path) -> None:
    pipeline = RecordingPipeline(discourses=[_discourse()])

    async with create_sqlite_checkpointer(
        database_path=tmp_path / "checkpoints.sqlite",
    ) as checkpointer:
        runner = pipeline.build_runner(
            run_id="run-1",
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            result = await runner.run(initial_state=_initial_state("run-1"))
        finally:
            runner.close()

    publication = result.get("publication_result")
    assert result.get("workflow_outcome") == WorkflowOutcome.PUBLISHED
    assert result.get("no_content_reason") is None
    assert result.get("episode_id") == EPISODE_ID
    assert publication is not None
    assert publication.episode_id == EPISODE_ID
    assert publication.guid == f"urn:pulse:{SHOW_ID}:{EPISODE_ID}"
    assert pipeline.events == _published_events()
    assert pipeline.events.index(PublishEpisodeNode.name) < pipeline.events.index(
        CommitSignalsNode.name
    )


@pytest.mark.asyncio
async def test_pipeline_graph_completes_without_episode(tmp_path: Path) -> None:
    pipeline = RecordingPipeline(discourses=[])

    async with create_sqlite_checkpointer(
        database_path=tmp_path / "checkpoints.sqlite",
    ) as checkpointer:
        runner = pipeline.build_runner(
            run_id="run-1",
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            result = await runner.run(initial_state=_initial_state("run-1"))
        finally:
            runner.close()

    assert result.get("workflow_outcome") == WorkflowOutcome.NO_CONTENT
    assert result.get("no_content_reason") == NoContentReason.NO_UNSEEN_SIGNALS
    assert "publication_result" not in result
    assert pipeline.events == [
        RetrieveSourcesNode.name,
        IngestSignalsNode.name,
    ]


@pytest.mark.asyncio
async def test_pipeline_graph_does_not_commit_when_publication_fails(tmp_path: Path) -> None:
    pipeline = RecordingPipeline(
        discourses=[_discourse()],
        fail_publications=1,
    )

    async with create_sqlite_checkpointer(
        database_path=tmp_path / "checkpoints.sqlite",
    ) as checkpointer:
        runner = pipeline.build_runner(
            run_id="run-1",
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            with pytest.raises(ValueError):
                await runner.run(initial_state=_initial_state("run-1"))

            checkpoint = await runner.get_state()
        finally:
            runner.close()

    assert CommitSignalsNode.name not in pipeline.events
    assert pipeline.events[-1] == PublishEpisodeNode.name
    assert checkpoint.get("workflow_outcome") is None
    assert "publication_result" not in checkpoint
    assert checkpoint["episode_id"] == EPISODE_ID


@pytest.mark.asyncio
async def test_pipeline_graph_resumes_same_logical_run(tmp_path: Path) -> None:
    run_id = "run-1"
    pipeline = RecordingPipeline(
        discourses=[_discourse()],
        fail_publications=1,
    )

    async with create_sqlite_checkpointer(
        database_path=tmp_path / "checkpoints.sqlite",
    ) as checkpointer:
        failed_runner = pipeline.build_runner(
            run_id=run_id,
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            with pytest.raises(ValueError):
                await failed_runner.run(initial_state=_initial_state(run_id))

            restored = await failed_runner.get_state()
            checkpoint = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": run_id}},
            )
        finally:
            failed_runner.close()

        assert checkpoint is not None
        configurable = checkpoint.config.get("configurable")
        assert configurable is not None
        assert configurable["thread_id"] == run_id
        assert restored["run_id"] == run_id
        assert restored["episode_id"] == EPISODE_ID
        assert "stored_episode_audio" in restored
        assert "publication_result" not in restored
        assert CommitSignalsNode.name not in pipeline.events

        unrelated = pipeline.build_runner(
            run_id="run-2",
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            assert "episode_id" not in await unrelated.get_state()
        finally:
            unrelated.close()

        resumed_runner = pipeline.build_runner(
            run_id=run_id,
            checkpointer=checkpointer,
            log_directory=tmp_path / "logs",
        )
        try:
            result = await resumed_runner.resume()
        finally:
            resumed_runner.close()

    publication = result.get("publication_result")
    assert result.get("workflow_outcome") == WorkflowOutcome.PUBLISHED
    assert result.get("episode_id") == EPISODE_ID
    assert publication is not None
    assert publication.episode_id == EPISODE_ID
    assert pipeline.published_episode_ids == [EPISODE_ID, EPISODE_ID]
    assert pipeline.events.count(RetrieveSourcesNode.name) == 1
    assert pipeline.events.count(ProduceAudioNode.name) == 1
    assert pipeline.events == [
        *_published_events()[: _published_events().index(PublishEpisodeNode.name)],
        PublishEpisodeNode.name,
        PublishEpisodeNode.name,
        CommitSignalsNode.name,
    ]

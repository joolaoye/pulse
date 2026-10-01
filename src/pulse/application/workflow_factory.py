from typing import Optional, TextIO

from pulse.application.composition.assemble import PulseApplication
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
from pulse.application.orchestration.runner.workflow_runner import (
    WorkflowRunner,
)
from pulse.application.runtime import PodcastPipelineRuntime


class PulseWorkflowFactory:
    def __init__(
        self,
        *,
        application: PulseApplication,
        run_log_stream: Optional[TextIO] = None,
    ) -> None:
        self._application = application
        self._run_log_stream = run_log_stream

    def create(
        self,
        *,
        run_id: str,
        runtime: PodcastPipelineRuntime,
    ) -> WorkflowRunner:
        if not run_id.strip():
            raise ValueError("Workflow run ID cannot be empty.")

        run_logger = RunLogger(
            run_id=run_id,
            pipeline_id=runtime.pipeline.pipeline_id,
            stream=self._run_log_stream,
        )
        node_logger = run_logger.node_logger

        graph_builder = PulseGraphBuilder(
            retrieve_sources_node=RetrieveSourcesNode(
                node_logger=node_logger,
                x_retriever=self._application.x_retriever,
                list_id=runtime.pipeline.x_list_id,
            ),
            ingest_signals_node=IngestSignalsNode(
                node_logger=node_logger,
                ingestor=runtime.ingestor,
            ),
            process_semantics_node=ProcessSemanticsNode(
                node_logger=node_logger,
                semantic_processor=runtime.semantic_processor,
            ),
            post_process_signals_node=PostProcessSignalsNode(
                node_logger=node_logger,
                post_processor=runtime.post_processor,
            ),
            group_signals_node=GroupSignalsNode(
                node_logger=node_logger,
                signal_group_builder=self._application.signal_group_builder,
            ),
            plan_episode_node=PlanEpisodeNode(
                node_logger=node_logger,
                planner=self._application.planner,
            ),
            generate_script_node=GenerateScriptNode(
                node_logger=node_logger,
                script_generator=self._application.script_generator,
            ),
            generate_episode_metadata_node=GenerateEpisodeMetadataNode(
                node_logger=node_logger,
                episode_metadata_generator=(self._application.episode_metadata_generator),
            ),
            produce_audio_node=ProduceAudioNode(
                node_logger=node_logger,
                audio_producer=self._application.audio_producer,
            ),
            publish_episode_node=PublishEpisodeNode(
                node_logger=node_logger,
                podcast_publisher=self._application.podcast_publisher,
            ),
            complete_without_episode_node=CompleteWithoutEpisodeNode(
                node_logger=node_logger,
            ),
            commit_signals_node=CommitSignalsNode(
                node_logger=node_logger,
                signal_committer=runtime.signal_committer,
            ),
        )

        return WorkflowRunner(
            run_id=run_id,
            graph_builder=graph_builder,
            checkpointer=self._application.checkpointer,
            run_logger=run_logger,
        )

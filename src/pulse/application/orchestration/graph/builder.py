from langgraph.graph import END, START, StateGraph

from pulse.application.orchestration.graph.retry_policies import (
    PUBLICATION_RETRY_POLICY,
    TRANSIENT_RETRY_POLICY,
)
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
from pulse.application.orchestration.nodes.errors import MissingNodeInputError
from pulse.application.orchestration.state import WorkflowState


class PulseGraphBuilder:
    def __init__(
        self,
        *,
        retrieve_sources_node: RetrieveSourcesNode,
        ingest_signals_node: IngestSignalsNode,
        process_semantics_node: ProcessSemanticsNode,
        post_process_signals_node: PostProcessSignalsNode,
        group_signals_node: GroupSignalsNode,
        plan_episode_node: PlanEpisodeNode,
        generate_script_node: GenerateScriptNode,
        generate_episode_metadata_node: GenerateEpisodeMetadataNode,
        produce_audio_node: ProduceAudioNode,
        publish_episode_node: PublishEpisodeNode,
        commit_signals_node: CommitSignalsNode,
        complete_without_episode_node: CompleteWithoutEpisodeNode,
    ) -> None:
        self._retrieve_sources_node = retrieve_sources_node
        self._ingest_signals_node = ingest_signals_node
        self._process_semantics_node = process_semantics_node
        self._post_process_signals_node = post_process_signals_node
        self._group_signals_node = group_signals_node
        self._plan_episode_node = plan_episode_node
        self._generate_script_node = generate_script_node
        self._generate_episode_metadata_node = generate_episode_metadata_node
        self._produce_audio_node = produce_audio_node
        self._publish_episode_node = publish_episode_node
        self._commit_signals_node = commit_signals_node
        self._complete_without_episode_node = complete_without_episode_node

    def build(self) -> StateGraph:
        graph = StateGraph(WorkflowState)
        self._add_nodes(graph=graph)
        self._add_edges(graph=graph)
        return graph

    def _add_nodes(
        self,
        *,
        graph: StateGraph,
    ) -> None:
        transient_nodes = (
            self._retrieve_sources_node,
            self._ingest_signals_node,
            self._process_semantics_node,
            self._post_process_signals_node,
            self._group_signals_node,
            self._plan_episode_node,
            self._generate_script_node,
            self._generate_episode_metadata_node,
            self._produce_audio_node,
        )

        for node in transient_nodes:
            graph.add_node(
                node.name,
                node,
                retry_policy=TRANSIENT_RETRY_POLICY,
            )

        graph.add_node(
            self._publish_episode_node.name,
            self._publish_episode_node,
            retry_policy=PUBLICATION_RETRY_POLICY,
        )
        graph.add_node(
            self._commit_signals_node.name,
            self._commit_signals_node,
            retry_policy=TRANSIENT_RETRY_POLICY,
        )
        graph.add_node(
            self._complete_without_episode_node.name,
            self._complete_without_episode_node,
        )

    def _add_edges(
        self,
        *,
        graph: StateGraph,
    ) -> None:
        graph.add_edge(
            START,
            self._retrieve_sources_node.name,
        )
        graph.add_edge(
            self._retrieve_sources_node.name,
            self._ingest_signals_node.name,
        )
        graph.add_conditional_edges(
            self._ingest_signals_node.name,
            self._has_unseen_signals,
            {
                True: self._process_semantics_node.name,
                False: self._complete_without_episode_node.name,
            },
        )
        graph.add_conditional_edges(
            self._process_semantics_node.name,
            self._has_embedded_signals,
            {
                True: self._post_process_signals_node.name,
                False: self._complete_without_episode_node.name,
            },
        )
        graph.add_conditional_edges(
            self._post_process_signals_node.name,
            self._has_processed_signals,
            {
                True: self._group_signals_node.name,
                False: self._complete_without_episode_node.name,
            },
        )

        graph.add_conditional_edges(
            self._group_signals_node.name,
            self._has_themed_signal_clusters,
            {
                True: self._plan_episode_node.name,
                False: self._complete_without_episode_node.name,
            },
        )

        graph.add_edge(
            self._plan_episode_node.name,
            self._generate_script_node.name,
        )
        graph.add_edge(
            self._generate_script_node.name,
            self._generate_episode_metadata_node.name,
        )
        graph.add_edge(
            self._generate_episode_metadata_node.name,
            self._produce_audio_node.name,
        )
        graph.add_edge(
            self._produce_audio_node.name,
            self._publish_episode_node.name,
        )
        graph.add_edge(
            self._publish_episode_node.name,
            self._commit_signals_node.name,
        )
        graph.add_edge(
            self._commit_signals_node.name,
            END,
        )
        graph.add_edge(
            self._complete_without_episode_node.name,
            END,
        )

    def _has_processed_signals(
        self,
        state: WorkflowState,
    ) -> bool:
        input_name = "processed_signals_by_id"

        if input_name not in state:
            raise MissingNodeInputError(
                node_name=self._post_process_signals_node.name,
                input_name=input_name,
            )

        return bool(state[input_name])

    def _has_themed_signal_clusters(
        self,
        state: WorkflowState,
    ) -> bool:
        input_name = "themed_signal_clusters"

        if input_name not in state:
            raise MissingNodeInputError(
                node_name=self._group_signals_node.name,
                input_name=input_name,
            )

        return bool(state[input_name])

    def _has_unseen_signals(
        self,
        state: WorkflowState,
    ) -> bool:
        input_name = "unseen_signals"

        if input_name not in state:
            raise MissingNodeInputError(
                node_name=self._ingest_signals_node.name,
                input_name=input_name,
            )

        return bool(state[input_name])

    def _has_embedded_signals(
        self,
        state: WorkflowState,
    ) -> bool:
        input_name = "embedded_signals_by_id"

        if input_name not in state:
            raise MissingNodeInputError(
                node_name=self._process_semantics_node.name,
                input_name=input_name,
            )

        return bool(state[input_name])

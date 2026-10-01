# Generation

Pulse's generation path turns the signals selected by semantic processing into a coherent, speaker-aware podcast episode and persisted audio.

Generation begins with `ProcessedSignal` objects and their corresponding embeddings. It ends with two publication-ready artifacts:

```text
EpisodeMetadata
StoredEpisodeAudio
```

The generation path spans five LangGraph stages:

```text
GroupSignalsNode
    ↓
PlanEpisodeNode
    ↓
GenerateScriptNode
    ↓
GenerateEpisodeMetadataNode
    ↓
ProduceAudioNode
```

These nodes remain thin orchestration boundaries. The actual grouping, planning, scripting, metadata generation, and audio production behavior lives in generation services.

---

## Overview

![Pulse generation architecture](../assets/pulse-generation-architecture.svg)

Conceptually:

```text
ProcessedSignal[]
        +
matching EmbeddedSignal[]
        ↓
SignalGroupBuilder
        ↓
ThemedSignalCluster[]
        ↓
Planner
        ↓
TurnPlan
        ↓
ScriptGenerator
        ↓
EpisodeScript
        ├── EpisodeMetadataGenerator
        │       ↓
        │   EpisodeMetadata
        │
        └── AudioProducer
                ↓
        StoredEpisodeAudio
```

The LangGraph workflow currently generates metadata before audio, but both are derived from the finalized `EpisodeScript`. Audio generation does not depend on episode metadata.

The generation subsystem therefore has four broad responsibilities:

```text
group related material
    ↓
plan what the episode should discuss
    ↓
realize that plan as spoken dialogue
    ↓
produce publication metadata and audio
```

---

## Grouping and clustering

`GroupSignalsNode` is the first generation-stage node.

Semantic processing has already decided which signals are eligible. Grouping does not repeat relevance filtering or semantic deduplication.

Instead, it asks:

> Which of the selected signals belong in the same editorial conversation?

`SignalGroupBuilder` coordinates two responsibilities:

```text
SignalClusterer
    +
ThemeExtractionAgent
```

The clustering stage uses the surviving signal embeddings to identify related material.

Conceptually:

```text
ProcessedSignal[]
        +
EmbeddedSignal[]
        ↓
match by signal_id
        ↓
SignalClusterer
        ↓
related signal groups
```

The embedding determines semantic proximity.

The corresponding `ProcessedSignal` objects provide the source and editorial context needed by downstream generation.

These representations must remain aligned by `signal_id`; grouping must not join them by list position.

---

## Theme extraction

After signals have been clustered, Pulse assigns an editorial theme to each group.

`SignalGroupBuilder` calls `ThemeExtractionAgent` directly. It is an Anthropic-backed generation agent.

Conceptually:

```text
related ProcessedSignal[]
        ↓
ThemeExtractionAgent
        ↓
Theme
        ↓
ThemedSignalCluster
```

The theme describes the common idea connecting the signals. It does not replace the underlying signals as factual source material.

The result of grouping is:

```text
ThemedSignalCluster[]
```

which becomes the input to episode planning.

If grouping produces no usable clusters, the workflow can complete successfully through the `NO_CONTENT` path rather than invoking the planner with no material.

---

## Planning

The root planning service is `Planner`.

It coordinates two major phases:

```text
EpisodePlanner
    ↓
EpisodePlan

TurnPlanner
    ↓
TurnPlan
```

Conceptually:

```text
ThemedSignalCluster[]
        +
target episode duration
        ↓
EpisodePlanner
        ↓
EpisodePlan
        +
SpeakerProfile[]
        ↓
TurnPlanner
        ↓
TurnPlan
```

`Planner` returns the finalized `TurnPlan`.

There is no separate `GenerationPlan`.

---

## Episode planning

Episode planning decides the structure and editorial purpose of the episode before any dialogue is written.

The stable episode hierarchy is:

```text
EpisodePlan
├── EpisodeOpening
├── EpisodeBody
│   └── Segment[]
│       └── Beat[]
└── EpisodeClosing
```

The hierarchy is deliberately structural.

A `Segment` represents a major section of the episode. A `Beat` represents one focused conversational topic within that segment.

Speaker assignment does not happen here. That belongs to turn planning.

---

## Body outline

The body is planned before its individual beats are expanded.

`BodyOutlinePlanner` produces a `BodyOutline` consisting of ordered `SegmentOutline` objects:

```text
BodyOutline
└── SegmentOutline[]
    ├── cluster_id
    ├── title
    ├── narrative_goal
    └── target_duration_seconds
```

A `SegmentOutline` therefore answers:

```text
which cluster should this section use?
what should this section accomplish?
where does it belong in the narrative?
how much body time does it receive?
```

The outline is not the final episode body.

It is the high-level plan used to construct finalized `Segment` objects.

---

## Shortlisting topics

Each outlined segment may contain several source signals, but not every possible combination deserves its own conversational beat.

`SegmentPlanner` therefore uses `ShortlistPlanner` before building beats.

The intermediate model is:

```text
Shortlist
└── Topic[]
    ├── primary_signal_id
    ├── supporting_signal_ids[]
    ├── editorial_goal
    └── duration_weight
```

A `Topic` identifies the primary source signal for one discussion topic and any supporting signals that materially strengthen it.

`duration_weight` is intentionally relative.

It expresses editorial importance within the segment; it is not a stable duration in seconds.

Conceptually:

```text
SegmentOutline
        +
ThemedSignalCluster
        ↓
ShortlistPlanner
        ↓
Shortlist
        ↓
relative Topic weights
        ↓
deterministic duration allocation
        ↓
exact Beat durations
```

For the current planning model:

> One selected `Topic` becomes one `Beat`.

---

## Beat planning

`BeatPlanner` turns a shortlisted topic into the actual editorial contract that downstream turn planning must realize.

A `Beat` contains:

```text
Beat
├── primary_signal_id
├── supporting_signal_ids[]
├── title
├── purpose
├── conversation_angle
├── questions
├── segue_transition?
└── target_duration_seconds
```

`BeatPlanner` coordinates two additional planning capabilities:

```text
ConversationAnglePlanner
QuestionPlanner
```

The resulting `ConversationAngle` defines the perspective and editorial framing of the discussion. Its model carries:

```text
title
perspective
central_thesis
narrative_hook
listener_value
tension
```

`ConversationQuestions` contains one or more `ConversationQuestion` objects:

```text
ConversationQuestion
├── question
└── rationale
```

These models define what makes the beat interesting and what the conversation should explore.

They do not contain final spoken dialogue.

The finalized body structure is:

```text
EpisodeBody
└── Segment[]
    ├── title
    ├── narrative_goal
    ├── target_duration_seconds
    └── Beat[]
```

---

## Opening and closing

Once the body has been planned, `EpisodePlanner` also produces an `EpisodeOpening` and `EpisodeClosing`.

The opening model carries the editorial contract for starting the episode, including:

```text
target_duration_seconds
objective
hook_strategy
podcast_introduction_goal
speaker_introduction_goal
listener_promise
transition_goal
```

The closing model carries:

```text
target_duration_seconds
objective
resolution_strategy
final_takeaway
closing_goal
```

The result is the stable `EpisodePlan`:

```text
EpisodePlan
├── opening: EpisodeOpening
├── body: EpisodeBody
└── closing: EpisodeClosing
```

Its total duration is derived from the duration of those three components.

---

## Turn planning

`EpisodePlan` says what the episode should accomplish.

`TurnPlanner` decides how the configured speakers should realize that plan conversationally.

The stable `Turn` model is:

```text
Turn
├── speaker_id
├── conversational_function
├── editorial_objective
└── target_duration_seconds
```

A `Turn` does not contain scripted dialogue.

It defines:

- who speaks;
- what conversational move they should make;
- what that turn must accomplish;
- how much speaking time it receives.

The three turn-planning capabilities are:

```text
OpeningTurnPlanner
BodyTurnPlanner
ClosingTurnPlanner
```

Opening turn planning works from the finalized opening, the first segment, and the available speakers.

Body turn planning works beat by beat. Each `Beat` is already self-contained enough to define its editorial objective, source references, conversational angle, questions, transition guidance, and duration.

Closing turn planning works from the finalized closing, the final segment, and the available speakers.

---

## `TurnPlan`

The root speaker-aware planning model is:

```text
TurnPlan
├── opening: OpeningTurnPlan
│   └── Turn[]
│
├── body: BodyTurnPlan
│   └── SegmentTurnPlan[]
│       └── BeatTurnPlan[]
│           └── Turn[]
│
└── closing: ClosingTurnPlan
    └── Turn[]
```

The body hierarchy intentionally mirrors the finalized episode structure:

```text
EpisodeBody
└── Segment[]
    └── Beat[]
```

becomes:

```text
BodyTurnPlan
└── SegmentTurnPlan[]
    └── BeatTurnPlan[]
        └── Turn[]
```

This preserves structural context through turn planning without forcing scripting to reconstruct the episode hierarchy.

---

## Duration authority

Duration is established during planning rather than guessed after the script has already been written.

Conceptually:

```text
target episode duration
        ↓
opening / body / closing budgets
        ↓
segment budgets
        ↓
beat budgets
        ↓
turn budgets
        ↓
script realization
        ↓
audio rendering
```

Where editorial judgment is useful, planning agents may return relative duration weights.

Python converts those weights deterministically into exact seconds before the corresponding stable model is created.

The stable models therefore carry exact duration values:

```text
SegmentOutline.target_duration_seconds
Segment.target_duration_seconds
Beat.target_duration_seconds
EpisodeOpening.target_duration_seconds
EpisodeClosing.target_duration_seconds
Turn.target_duration_seconds
```

The important conservation relationships are:

```text
sum Turn durations for a Beat
    = Beat duration

sum Beat durations for a Segment
    = Segment duration

sum Segment durations
    = EpisodeBody duration

opening + body + closing
    = EpisodePlan duration

TurnPlan duration
    = planned episode duration
```

This prevents downstream stages from inventing unbudgeted episode structure.

---

## Planned duration vs actual audio duration

Planning duration and synthesized duration are related but not identical concepts.

A `Turn.target_duration_seconds` is an authoritative generation budget. The scripting layer uses it when realizing the turn.

The actual duration of synthesized speech is measured later from the TTS output.

Conceptually:

```text
planned seconds
    ↓
script realization
    ↓
ElevenLabs synthesis
    ↓
measured audio duration
```

Pulse does not silently truncate spoken content to force the waveform to exactly match the planning target.

The assembled `EpisodeAudio` records the actual `duration_seconds`, which is the value used by publishing.

This distinction is important:

```text
planning duration
    → structural authority

audio duration
    → measured playback reality
```

---

## Podcast and speaker profiles

Generation uses two different kinds of persistent editorial configuration.

### `PodcastProfile`

The podcast profile describes how generated episodes should sound editorially:

```text
PodcastProfile
├── name
├── purpose
├── target_audience
├── editorial_style
└── conversational_style
```

It is generation configuration.

It is separate from `PodcastShow`, which owns public RSS and publication identity.

The current generation path uses `PodcastProfile` when realizing the script so that individual turns fit the show's overall editorial and conversational style.

It should not be confused with source material: the podcast profile controls presentation, not factual claims.

### `SpeakerProfile`

Each configured speaker has:

```text
SpeakerProfile
├── speaker_id
├── display_name
├── podcast_role
├── persona
├── expertise[]
└── speaking_style
```

Speaker profiles are used during turn planning and scripting.

Turn planning uses them to decide which conversational move naturally belongs to which speaker.

Scripting uses the resolved profile to realize that speaker's planned turn consistently.

The stable `speaker_id` then continues through the entire downstream path:

```text
SpeakerProfile
    ↓
Turn.speaker_id
    ↓
ScriptTurn.speaker_id
    ↓
DialogueBatchTurn.speaker_id
    ↓
EpisodeTurnTiming.speaker_id
```

---

## Script generation

`GenerateScriptNode` delegates to `ScriptGenerator`.

The scripting architecture is intentionally flat.

The stable models are:

```text
EpisodeScript
└── turns: ScriptTurn[]

ScriptTurn
├── speaker_id
└── spoken_text
```

There is no separate stable opening/body/closing script hierarchy.

In particular, V1 does not use:

```text
ScriptSection
EpisodeScript.opening
EpisodeScript.episode_beats
EpisodeScript.closing
```

The planning hierarchy already contains the structural information required to generate dialogue.

---

## `TurnGenerator`

`TurnGenerator` walks the finalized `TurnPlan` in episode order.

Each planned `Turn` is realized by the same generic `TurnScriptingAgent`:

```text
1 Turn
    +
resolved SpeakerProfile
    +
PodcastProfile
    +
local planning context
    +
relevant ProcessedSignal source context
    ↓
TurnScriptingAgent
    ↓
spoken_text
    ↓
ScriptTurn
```

Python preserves the planned speaker assignment:

```text
Turn.speaker_id
    ↓
ScriptTurn.speaker_id
```

The language model generates spoken text; it does not get to reassign the speaker.

For body turns, source grounding is resolved through the signal IDs already stored on the parent `Beat`:

```text
Beat.primary_signal_id
Beat.supporting_signal_ids
        ↓
resolve ProcessedSignal context
        ↓
TurnScriptingAgent
```

Stable IDs, rather than list positions, connect planning back to source material.

---

## Planning authority and factual authority

Planning and source context serve different purposes.

Conceptually:

```text
planning models
    → editorial authority

ProcessedSignal
    → factual authority
```

Planning determines:

```text
what to discuss
how to frame it
what question to pursue
which speaker should make which move
how long the discussion should last
```

The selected source material determines the facts available to support that discussion.

Scripting should realize the plan without treating newly invented planning prose as an independent factual source.

---

## Conversation polish

The initial script is passed through `ConversationPolisher`.

Polishing happens sequentially at the turn level:

```text
ScriptTurn
    +
resolved SpeakerProfile
    +
previous polished ScriptTurn?
    ↓
ConversationPolishAgent
    ↓
polished spoken_text
```

Python again retains the original `speaker_id`.

Conversation polishing is not another episode-planning pass.

Its responsibility is local conversational and delivery refinement:

```text
planning
    → what should be said

turn scripting
    → spoken realization

conversation polish
    → delivery and immediate conversational flow
```

The current ElevenLabs runtime delivery instructions and examples are injected into `ConversationPolishAgent`, allowing supported delivery annotations to be introduced close to the synthesis boundary without coupling the planning system to the TTS provider.

The result remains the same public model:

```text
EpisodeScript
```

---

## Episode metadata

After the final script is produced, `GenerateEpisodeMetadataNode` delegates to `EpisodeMetadataGenerator`.

The generator uses `EpisodeMetadataGenerationAgent` to derive publication-facing metadata from the finalized `EpisodeScript`.

The stable model is:

```text
EpisodeMetadata
├── title
└── description
```

Metadata generation does not plan the episode or modify the script.

It summarizes the episode that was actually written.

This separation also prevents synthesis-specific delivery annotations from becoming part of the podcast's public editorial structure.

---

## Audio production

`ProduceAudioNode` delegates to `AudioProducer`.

The current audio path is:

```text
EpisodeScript
    +
SpeakerVoiceBinding[]
    ↓
DialogueBatcher
    ↓
DialogueBatch[]
    ↓
DialogueSynthesizer
    ↓
ElevenLabsDialogueProvider
    ↓
SynthesizedDialogueBatch[]
    ↓
AudioAssembler
    ↓
EpisodeAudio
    ↓
AudioRepository
    ↓
StoredEpisodeAudio
```

Audio production is intentionally mechanical.

By this point:

```text
content is finalized
speaker assignment is finalized
turn ordering is finalized
spoken text is finalized
```

The audio subsystem should not make editorial decisions.

---

## Speaker voice bindings

A `SpeakerProfile` describes a speaker editorially.

A `SpeakerVoiceBinding` connects that speaker to synthesis infrastructure:

```text
SpeakerVoiceBinding
├── speaker_id
└── voice_id
```

This keeps the two concerns separate:

```text
SpeakerProfile
    → who this speaker is

SpeakerVoiceBinding
    → which provider voice speaks for them
```

A voice can therefore be changed without changing episode planning or speaker identity.

---

## Audio batching

`DialogueBatcher` converts the flat script into provider-sized synthesis batches.

For every `ScriptTurn`, it resolves the configured voice and creates:

```text
DialogueBatchTurn
├── script_turn_index
├── speaker_id
├── voice_id
└── spoken_text
```

Those turns are packed into:

```text
DialogueBatch
├── batch_index
└── turns: DialogueBatchTurn[]
```

`DialogueBatch` also exposes its aggregate character count so batching can respect provider request-size constraints.

The important distinction is:

> Audio batching is a transport concern, not an editorial structure.

A batch boundary does not correspond to a segment, beat, or change in podcast topic.

The original global `script_turn_index` is preserved so batches can later be reassembled without losing script order.

---

## ElevenLabs synthesis

`DialogueSynthesizer` converts each `DialogueBatch` into provider dialogue inputs:

```text
spoken_text
    +
voice_id
    ↓
ElevenLabsDialogueProvider
```

The provider returns encoded audio and timing information.

Pulse converts each successful response into:

```text
SynthesizedDialogueBatch
├── batch_index
├── audio_content
├── output_format
├── duration_seconds
└── turn_timings[]
```

Batch-relative turn timings preserve:

```text
script_turn_index
speaker_id
start_time_seconds
end_time_seconds
```

`DialogueSynthesizer` also owns bounded retry behavior for retryable ElevenLabs provider failures.

Provider retry behavior therefore remains inside the audio capability rather than becoming episode-planning logic.

---

## Audio assembly

`AudioAssembler` consumes the ordered synthesized batches.

For the current MP3 path it:

```text
validates batch ordering
    ↓
parses synthesized MP3 batches
    ↓
preserves global script-turn ordering
    ↓
converts batch-relative timings to episode-relative timings
    ↓
concatenates the encoded audio
    ↓
produces EpisodeAudio
```

`EpisodeAudio` contains:

```text
EpisodeAudio
├── audio_content
├── output_format
├── duration_seconds
└── turn_timings[]
```

Its timing validation requires the global script-turn indexes to remain contiguous and in their original order.

The final `duration_seconds` is derived from the assembled audio rather than copied from the episode's planning target.

---

## Audio persistence

The assembled audio is persisted through `AudioRepository`.

The workflow therefore does not need to carry complete audio bytes into later publication stages.

The durable result is:

```text
StoredEpisodeAudio
├── object_key
├── output_format
├── duration_seconds
├── size_bytes
└── turn_timings[]
```

The audio object itself lives in R2.

The persisted model contains the information required by publication to construct the episode enclosure and RSS metadata.

Publishing remains a separate pipeline stage.

---

## Agent and provider boundaries

Generation uses several narrow AI agents rather than one model call responsible for the entire episode.

| Capability | Agent / provider | Responsibility |
| --- | --- | --- |
| Theme extraction | `ThemeExtractionAgent` | Describe the common editorial theme of a signal cluster |
| Body outlining | `BodyOutlinePlanningAgent` | Select and order body segments and allocate high-level body structure |
| Shortlisting | `ShortlistPlanningAgent` | Select the topics worth developing within a segment |
| Beat planning | `BeatPlanningAgent` | Define the purpose of one finalized beat |
| Conversation angle | `ConversationAnglePlanningAgent` | Choose the beat's perspective, thesis, hook, value, and tension |
| Question planning | `QuestionPlanningAgent` | Generate questions that develop the beat |
| Opening planning | `OpeningPlanningAgent` | Define the episode-opening editorial contract |
| Closing planning | `ClosingPlanningAgent` | Define the episode-closing editorial contract |
| Opening turns | `OpeningTurnPlanningAgent` | Allocate speaker-aware opening turns |
| Body turns | `BodyTurnPlanningAgent` | Allocate speaker-aware turns for a finalized beat |
| Closing turns | `ClosingTurnPlanningAgent` | Allocate speaker-aware closing turns |
| Turn scripting | `TurnScriptingAgent` | Realize one planned turn as spoken text |
| Conversation polish | `ConversationPolishAgent` | Refine local delivery and conversational continuity |
| Episode metadata | `EpisodeMetadataGenerationAgent` | Generate the episode title and description |
| Speech synthesis | `ElevenLabsDialogueProvider` | Render finalized spoken text as audio |

The editorial and scripting agents are currently backed by Anthropic.

Each agent owns its own model configuration, including model selection, temperature, and token limit. Those implementation constants remain the source of truth; this architecture document does not duplicate exact provider model IDs.

ElevenLabs has a narrower role:

```text
final spoken text
    ↓
speech synthesis
```

It does not plan topics, choose speakers, or rewrite the episode.

---

## Prompt boundaries

Prompt internals are intentionally not reproduced in the public architecture documentation.

The important architectural contracts are what each agent is allowed to decide.

For example:

```text
BodyOutlinePlanningAgent
    → episode-body structure

ShortlistPlanningAgent
    → which source-grounded topics to develop

BeatPlanningAgent
    → one beat's editorial purpose

TurnPlanningAgent
    → speaker assignment and conversational function

TurnScriptingAgent
    → exact spoken realization

ConversationPolishAgent
    → local conversational and delivery refinement
```

The full system prompts, few-shot examples, preservation rules, and provider-specific instructions are implementation details.

Keeping them out of this document prevents prompt wording from becoming a second architectural contract.

A useful authority rule across the generation system is:

> Planning owns editorial structure. Source material owns factual grounding. Scripting realizes the plan. Audio renders the finalized script.

---

## LangGraph boundaries

LangGraph coordinates generation at aggregate service boundaries:

```text
GroupSignalsNode
    → SignalGroupBuilder

PlanEpisodeNode
    → Planner

GenerateScriptNode
    → ScriptGenerator

GenerateEpisodeMetadataNode
    → EpisodeMetadataGenerator

ProduceAudioNode
    → AudioProducer
```

The graph does not create one node per planning agent, script turn, or audio batch.

Those finer-grained operations remain internal to their cohesive services.

This keeps checkpointing and retry boundaries aligned with meaningful episode-production stages rather than individual model calls.

---

## Architectural boundaries

The generation subsystem owns:

```text
signal grouping
theme extraction
episode planning
turn planning
script generation
conversation polish
episode metadata generation
audio batching
speech synthesis
audio assembly
audio persistence
```

It does not own:

```text
source retrieval
exact deduplication
semantic deduplication
interest relevance filtering
RSS publication
episode publication records
signal-history commit
```

The complete boundary is:

```text
semantic processing
    ↓
ProcessedSignal[]
    ↓
generation
    ↓
ThemedSignalCluster[]
    ↓
TurnPlan
    ↓
EpisodeScript
    ├── EpisodeMetadata
    └── StoredEpisodeAudio
    ↓
publishing
```

---

## Related documentation

- [System architecture](../architecture.md) — top-level runtime and workflow boundaries.
- [Retrieval](retrieval.md) — X source retrieval and discourse reconstruction.
- [Semantic processing](semantics.md) — canonical signals, deduplication, relevance, and `ProcessedSignal`.
- [Publishing](publishing.md) — episode publication, RSS generation, and signal-history commit.
- [Configuration](../configuration.md) — podcast profiles, speaker profiles, voice bindings, and target duration.
- [Operations](../operations.md) — observing and troubleshooting deployed generation runs.
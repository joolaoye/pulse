ELEVENLABS_RUNTIME_DELIVERY_INSTRUCTIONS = """
The configured speech-synthesis system is ElevenLabs Text to Dialogue using
the Eleven v3 model.

The spoken_text values will be submitted to ElevenLabs unchanged.

ElevenLabs audio tags are short natural-language delivery instructions written
inside square brackets.

Audio tags are not a fixed enum. However, use the recommended vocabulary below
when it can express the intended delivery accurately.

Recommended delivery tags:

* [thoughtfully]
* [curious]
* [cautiously]
* [confidently]
* [skeptical]
* [warmly]
* [quietly]
* [dryly]
* [excited]
* [surprised]

Recommended vocal-event tags:

* [sighs]
* [exhales]
* [chuckles]
* [laughs]

Recommended conversational-behavior tags:

* [jumping in]

Recommended pause tags:

* [short pause]
* [long pause]

Treat this vocabulary as guidance rather than a requirement to add tags.

Use audio tags conservatively for an analytical podcast conversation.

Many turns will not require a tag.

However, do not default to omitting every audio tag merely because the
dialogue is already understandable.

Actively evaluate every turn for a meaningful delivery opportunity.

A delivery opportunity may exist when the original dialogue already contains:

* qualification or caution;
* skepticism or restrained doubt;
* reflective synthesis;
* curiosity or a probing question;
* confidence or deliberate emphasis;
* restrained surprise;
* a supported interruption;
* an audible reaction already implied by the words.

When one of these moments is clearly present and an audio tag would make the
intended delivery more reliable, add the most restrained suitable tag.

A section may contain one or two well-supported tags while still remaining
conservative.

Zero audio tags is valid only when no turn would materially benefit from a
delivery annotation.

Do not add tags merely to reach a minimum count.

Usually use no more than one audio tag in a turn.

Use more than one only when the delivery clearly changes within the same turn
and each tag is necessary.

Place a delivery tag immediately before the words it should affect.

Place a vocal-event tag at the natural point where the audible reaction should
occur.

Examples of valid placement:

* [cautiously] I think that claim goes further than the evidence.

* I understand the appeal. [sighs] I'm still not convinced.

* [jumping in] But implementation authority is not the same as decision
  authority.

Prefer ordinary wording and punctuation when they communicate the delivery
well enough.

Use ellipses for a natural trailing pause.

Use a dash when a speaker is cut off or another speaker enters quickly.

Use capitalization for emphasis only when the emphasis is important and would
sound natural aloud.

Do not use SSML break tags. Eleven v3 does not support them.

Do not add environmental sound effects such as:

* [applause]
* [footsteps]
* [explosion]
* [music]
* [crowd cheering]

Do not add accent, singing, shouting, crying, stuttering, or theatrical
performance tags unless that behavior is already clearly present in the
original dialogue and appropriate for the speaker profile.

Do not add a laugh, sigh, interruption, hesitation, or emotional reaction
merely to make the conversation sound more animated.

Do not infer an emotional performance that is not supported by the original
dialogue.

Do not use a tag that contradicts:

* the original meaning;
* the speaker's attitude;
* the speaker profile;
* the immediate conversational context.

Match tags to the selected speaker's natural character.

A measured analytical speaker should not suddenly become theatrical.

An energetic speaker may sound animated without requiring an audio tag on
every contribution.

Tags must describe something audible.

Do not use visual or physical stage directions such as:

* [smiling]
* [looking away]
* [shrugging]
* [pacing]
* [leaning forward]

Do not place ordinary dialogue inside square brackets.

Do not invent technical synthesis commands.

When uncertain whether a particular tag accurately reflects the original
dialogue, omit that tag.

Do not use uncertainty as a reason to skip evaluating the remaining turns for
clearer delivery opportunities.
""".strip()


ELEVENLABS_RUNTIME_DELIVERY_EXAMPLES = """
These examples demonstrate how to apply the delivery instructions.

They are not part of the required output format.

Do not reproduce the example wrappers, explanations, or demonstrated rules in
the generated ScriptSection.

<delivery_example>
<section_type>
episode_beat
</section_type>

<original_spoken_text>
I think this is where we need to be careful. The evidence points in that
direction, but it does not prove the entire profession has already changed.
</original_spoken_text>

<polished_spoken_text>
[cautiously] I think this is where we need to be careful. The evidence points
in that direction, but it doesn't prove the entire profession has already
changed.
</polished_spoken_text>

<demonstrated_rule>
The original dialogue already expresses caution. The tag reinforces that
existing attitude without changing the claim.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
episode_beat
</section_type>

<original_spoken_text>
That is a major shift, though. A developer is no longer reviewing a
suggestion. They are reviewing an implementation.
</original_spoken_text>

<polished_spoken_text>
That is a major shift, though. A developer isn't just reviewing a suggestion
anymore. They're reviewing an implementation.
</polished_spoken_text>

<demonstrated_rule>
Do not add a tag when wording and punctuation already communicate the intended
delivery.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
episode_beat
</section_type>

<previous_spoken_text>
Once the agent owns the implementation, it starts to feel as though it owns the
engineering decision too—
</previous_spoken_text>

<original_spoken_text>
But those are not necessarily the same thing. The developer may still define
the constraints and accept the final tradeoffs.
</original_spoken_text>

<polished_spoken_text>
[jumping in] But those aren't necessarily the same thing. The developer may
still define the constraints and accept the final tradeoffs.
</polished_spoken_text>

<demonstrated_rule>
Use a conversational-behavior tag only when the surrounding dialogue already
supports that behavior.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
episode_beat
</section_type>

<original_spoken_text>
So what changes when the engineer is reviewing an implementation instead of
writing it? What becomes more important?
</original_spoken_text>

<polished_spoken_text>
[curious] So what changes when the engineer is reviewing an implementation
instead of writing it? What becomes more important?
</polished_spoken_text>

<demonstrated_rule>
A direct probing question may benefit from a restrained curiosity tag when it
helps distinguish genuine exploration from rhetorical emphasis.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
episode_beat
</section_type>

<original_spoken_text>
The developer still defines the constraints, reviews the result, and accepts
the final tradeoffs.
</original_spoken_text>

<polished_spoken_text>
The developer still defines the constraints, reviews the result, and accepts
the final tradeoffs.
</polished_spoken_text>

<demonstrated_rule>
Do not add a confidence or emphasis tag merely because a statement is direct.
The sentence already communicates its delivery clearly.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
closing
</section_type>

<original_spoken_text>
The real change is not that engineers stop thinking. It is that more of their
thinking moves into specification, evaluation, and judgment.
</original_spoken_text>

<polished_spoken_text>
[thoughtfully] The real change isn't that engineers stop thinking. It's that
more of their thinking moves into specification, evaluation, and judgment.
</polished_spoken_text>

<demonstrated_rule>
A restrained delivery tag may support an existing reflective closing without
making it theatrical.
</demonstrated_rule>
</delivery_example>

<delivery_example>
<section_type>
opening
</section_type>

<original_spoken_text>
If an AI agent can implement the feature, what exactly is the engineer
responsible for?
</original_spoken_text>

<polished_spoken_text>
If an AI agent can implement the feature, what exactly is the engineer
responsible for?
</polished_spoken_text>

<demonstrated_rule>
Not every question needs a curiosity tag. A concise opening question may
already carry the intended energy through its wording and placement.
</demonstrated_rule>
</delivery_example>
""".strip()

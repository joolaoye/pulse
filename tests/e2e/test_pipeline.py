import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional
from xml.etree import ElementTree

from dotenv import load_dotenv
import httpx
import pytest

from pulse.application.composition.local import (
    bootstrap_local,
)
from pulse.application.configuration import (
    PipelineManager,
    PodcastPipelineUpdate,
    PodcastShowUpdate,
    ShowManager,
    bootstrap_configuration,
)
from pulse.application.configuration.errors import (
    PodcastPipelineNotFoundError,
    PodcastShowNotFoundError,
)
from pulse.application.execution.errors import (
    WorkflowRunFailedError,
)
from pulse.application.execution.run_manager import (
    RunManager,
)
from pulse.application.orchestration.state import (
    WorkflowState,
)
from pulse.types import (
    PodcastPipeline,
    PodcastProfile,
    PodcastShow,
    SpeakerProfile,
    SpeakerVoiceBinding,
    WorkflowOutcome,
)

load_dotenv()


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pulse_test_pipeline.json"


def load_test_config() -> Dict[str, Any]:
    with FIXTURE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def create_podcast_show(
    *,
    config: Dict[str, Any],
    public_podcast_base_url: str,
) -> PodcastShow:
    show = config["show"]
    base_url = public_podcast_base_url.rstrip("/")

    artwork_url = f"{base_url}/shows/{show['show_id']}/artwork.jpg"

    return PodcastShow.model_validate(
        {
            **show,
            "website_url": base_url,
            "artwork_url": artwork_url,
            "verification_email": None,
            "public_base_url": base_url,
        }
    )


def create_podcast_pipeline(
    *,
    config: Dict[str, Any],
    x_list_id: str,
) -> PodcastPipeline:
    pipeline = config["pipeline"]

    return PodcastPipeline(
        pipeline_id=pipeline["pipeline_id"],
        show_id=config["show"]["show_id"],
        podcast_profile=(
            PodcastProfile.model_validate(
                pipeline["podcast_profile"],
            )
        ),
        speakers=[SpeakerProfile.model_validate(speaker) for speaker in pipeline["speakers"]],
        speaker_voice_bindings=[
            SpeakerVoiceBinding.model_validate(binding)
            for binding in pipeline["speaker_voice_bindings"]
        ],
        interest_profile_markdown=(pipeline["interest_profile_markdown"]),
        x_list_id=x_list_id,
        target_episode_duration_seconds=(pipeline["target_episode_duration_seconds"]),
        enabled=pipeline["enabled"],
    )


async def persist_podcast_show(
    *,
    show_manager: ShowManager,
    podcast_show: PodcastShow,
) -> PodcastShow:
    try:
        await show_manager.get(
            show_id=podcast_show.show_id,
        )

    except PodcastShowNotFoundError:
        return await show_manager.create(
            podcast_show=podcast_show,
        )

    return await show_manager.update(
        show_id=podcast_show.show_id,
        update=PodcastShowUpdate(
            title=podcast_show.title,
            description=podcast_show.description,
            author=podcast_show.author,
            website_url=podcast_show.website_url,
            artwork_url=podcast_show.artwork_url,
            category=podcast_show.category,
            language=podcast_show.language,
            explicit=podcast_show.explicit,
            verification_email=(podcast_show.verification_email),
            public_base_url=(podcast_show.public_base_url),
            feed_object_key=(podcast_show.feed_object_key),
        ),
    )


async def persist_podcast_pipeline(
    *,
    pipeline_manager: PipelineManager,
    pipeline: PodcastPipeline,
) -> PodcastPipeline:
    try:
        await pipeline_manager.get(
            pipeline_id=pipeline.pipeline_id,
        )

    except PodcastPipelineNotFoundError:
        return await pipeline_manager.create(
            pipeline=pipeline,
        )

    updated_pipeline = await pipeline_manager.update(
        pipeline_id=pipeline.pipeline_id,
        update=PodcastPipelineUpdate(
            show_id=pipeline.show_id,
            podcast_profile=(pipeline.podcast_profile),
            speakers=pipeline.speakers,
            speaker_voice_bindings=(pipeline.speaker_voice_bindings),
            interest_profile_markdown=(pipeline.interest_profile_markdown),
            x_list_id=pipeline.x_list_id,
            target_episode_duration_seconds=(pipeline.target_episode_duration_seconds),
        ),
    )

    if not updated_pipeline.enabled:
        updated_pipeline = await pipeline_manager.enable(
            pipeline_id=(updated_pipeline.pipeline_id),
        )

    return updated_pipeline


async def seed_test_pipeline(
    *,
    config: Dict[str, Any],
    x_list_id: str,
    public_podcast_base_url: str,
) -> PodcastPipeline:
    podcast_show = create_podcast_show(
        config=config,
        public_podcast_base_url=(public_podcast_base_url),
    )

    podcast_pipeline = create_podcast_pipeline(
        config=config,
        x_list_id=x_list_id,
    )

    async with bootstrap_configuration() as application:
        persisted_show = await persist_podcast_show(
            show_manager=application.show_manager,
            podcast_show=podcast_show,
        )

        persisted_pipeline = await persist_podcast_pipeline(
            pipeline_manager=(application.pipeline_manager),
            pipeline=podcast_pipeline,
        )

        persisted_show = await application.show_manager.get(
            show_id=persisted_show.show_id,
        )

        persisted_pipeline = await application.pipeline_manager.get(
            pipeline_id=(persisted_pipeline.pipeline_id),
        )

    assert persisted_pipeline.show_id == persisted_show.show_id

    assert persisted_pipeline.enabled

    return persisted_pipeline


async def run_test_pipeline(
    *,
    pipeline_id: str,
    resume_run_id: Optional[str],
) -> WorkflowState:
    async with bootstrap_local() as application:
        run_manager = RunManager(
            application=application,
        )

        try:
            if resume_run_id is not None:
                return await run_manager.resume(
                    run_id=resume_run_id,
                    pipeline_id=pipeline_id,
                )

            return await run_manager.run(
                pipeline_id=pipeline_id,
            )

        except WorkflowRunFailedError as error:
            raise AssertionError(
                "Pulse E2E workflow failed.\n"
                f"Pipeline ID: {error.pipeline_id}\n"
                f"Run ID: {error.run_id}\n"
                f"Error: {error.error}\n\n"
                "Resume with:\n"
                "pytest tests/e2e/test_pipeline.py "
                "-m e2e "
                f"--resume-run-id={error.run_id} ..."
            ) from error


def assert_published_result(
    *,
    result: WorkflowState,
    public_podcast_base_url: str,
) -> None:
    assert result.get("workflow_outcome") == WorkflowOutcome.PUBLISHED, (
        "The live publication E2E must reach "
        "WorkflowOutcome.PUBLISHED. "
        f"Actual outcome: "
        f"{result.get('workflow_outcome')!r}. "
        f"No-content reason: "
        f"{result.get('no_content_reason')!r}."
    )

    assert result.get("no_content_reason") is None

    episode_metadata = result.get("episode_metadata")
    stored_episode_audio = result.get("stored_episode_audio")
    publication_result = result.get("publication_result")

    assert episode_metadata is not None
    assert stored_episode_audio is not None
    assert publication_result is not None

    base_url = public_podcast_base_url.rstrip("/")

    expected_audio_url = f"{base_url}/{stored_episode_audio.object_key.lstrip('/')}"

    audio_url = str(publication_result.audio_url)
    feed_url = str(publication_result.feed_url)

    assert audio_url == expected_audio_url

    assert feed_url.startswith(f"{base_url}/")


async def assert_public_publication(
    *,
    result: WorkflowState,
) -> None:
    publication_result = result.get("publication_result")

    assert publication_result is not None

    feed_url = str(publication_result.feed_url)
    audio_url = str(publication_result.audio_url)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        feed_response = await client.get(
            feed_url,
        )

        assert feed_response.status_code == 200

        feed_content_type = feed_response.headers.get("content-type", "").split(";", 1)[0].lower()

        assert feed_content_type == "application/rss+xml"

        audio_response = await client.head(
            audio_url,
        )

        assert audio_response.status_code == 200

        audio_content_type = audio_response.headers.get("content-type", "").split(";", 1)[0].lower()

        assert audio_content_type == "audio/mpeg"

    root = ElementTree.fromstring(
        feed_response.content,
    )

    enclosure_urls = [
        enclosure.attrib.get("url") for enclosure in root.findall("./channel/item/enclosure")
    ]

    assert audio_url in enclosure_urls, (
        "Published audio URL was not found as an enclosure in the RSS feed."
    )


def print_e2e_result(
    *,
    result: WorkflowState,
) -> None:
    publication_result = result.get("publication_result")
    episode_metadata = result.get("episode_metadata")
    stored_audio = result.get("stored_episode_audio")

    print()
    print("=" * 80)
    print("PULSE LIVE E2E PASSED")
    print("=" * 80)
    print(f"Run ID: {result['run_id']}")
    print(f"Pipeline ID: {result['pipeline_id']}")
    print(f"Episode ID: {result['episode_id']}")

    if episode_metadata is not None:
        print(f"Episode: {episode_metadata.title}")

    if stored_audio is not None:
        print(f"Audio duration: {stored_audio.duration_seconds:.2f}s")
        print(f"Audio size: {stored_audio.size_bytes} bytes")

    if publication_result is not None:
        print(f"Audio URL: {publication_result.audio_url}")
        print(f"Feed URL: {publication_result.feed_url}")

    print("=" * 80)
    print()


async def run_live_e2e(
    *,
    x_list_id: str,
    public_podcast_base_url: str,
    resume_run_id: Optional[str],
) -> None:
    config = load_test_config()

    pipeline = await seed_test_pipeline(
        config=config,
        x_list_id=x_list_id,
        public_podcast_base_url=(public_podcast_base_url),
    )

    result = await run_test_pipeline(
        pipeline_id=pipeline.pipeline_id,
        resume_run_id=resume_run_id,
    )

    assert_published_result(
        result=result,
        public_podcast_base_url=(public_podcast_base_url),
    )

    await assert_public_publication(
        result=result,
    )

    print_e2e_result(
        result=result,
    )


@pytest.mark.e2e
def test_live_publication_pipeline(
    x_list_id: str,
    public_podcast_base_url: str,
    resume_run_id: Optional[str],
) -> None:
    asyncio.run(
        run_live_e2e(
            x_list_id=x_list_id,
            public_podcast_base_url=(public_podcast_base_url),
            resume_run_id=resume_run_id,
        )
    )

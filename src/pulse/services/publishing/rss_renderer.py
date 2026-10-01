from datetime import datetime, timezone
from email.utils import format_datetime
from typing import List, Set
from xml.etree import ElementTree

from pulse.types import EpisodePublication, PodcastShow

ITUNES_NAMESPACE = "http://www.itunes.com/dtds/podcast-1.0.dtd"

ElementTree.register_namespace(
    "itunes",
    ITUNES_NAMESPACE,
)


class RssFeedRenderer:
    def render(
        self,
        *,
        podcast_show: PodcastShow,
        episode_publications: List[EpisodePublication],
    ) -> bytes:
        self._validate_episode_publications(
            podcast_show=podcast_show,
            episode_publications=episode_publications,
        )

        ordered_publications = sorted(
            episode_publications,
            key=lambda publication: (
                publication.published_at,
                publication.episode_id,
            ),
            reverse=True,
        )

        rss = ElementTree.Element(
            "rss",
            {"version": "2.0"},
        )
        channel = ElementTree.SubElement(
            rss,
            "channel",
        )

        self._render_channel_metadata(
            channel=channel,
            podcast_show=podcast_show,
        )

        for publication in ordered_publications:
            self._render_episode_item(
                channel=channel,
                podcast_show=podcast_show,
                publication=publication,
            )

        ElementTree.indent(
            rss,
            space="    ",
        )

        return ElementTree.tostring(
            rss,
            encoding="utf-8",
            xml_declaration=True,
        )

    def _render_channel_metadata(
        self,
        *,
        channel: ElementTree.Element,
        podcast_show: PodcastShow,
    ) -> None:
        self._append_text(
            channel,
            "title",
            podcast_show.title,
        )
        self._append_text(
            channel,
            "link",
            str(podcast_show.website_url),
        )
        self._append_text(
            channel,
            "description",
            podcast_show.description,
        )
        self._append_text(
            channel,
            "language",
            podcast_show.language,
        )
        self._append_text(
            channel,
            self._itunes_tag("author"),
            podcast_show.author,
        )

        ElementTree.SubElement(
            channel,
            self._itunes_tag("image"),
            {
                "href": str(podcast_show.artwork_url),
            },
        )

        ElementTree.SubElement(
            channel,
            self._itunes_tag("category"),
            {
                "text": podcast_show.category,
            },
        )

        self._append_text(
            channel,
            self._itunes_tag("explicit"),
            "true" if podcast_show.explicit else "false",
        )

        if podcast_show.verification_email is not None:
            self._render_owner_metadata(
                channel=channel,
                podcast_show=podcast_show,
            )

    def _render_owner_metadata(
        self,
        *,
        channel: ElementTree.Element,
        podcast_show: PodcastShow,
    ) -> None:
        owner = ElementTree.SubElement(
            channel,
            self._itunes_tag("owner"),
        )

        self._append_text(
            owner,
            self._itunes_tag("name"),
            podcast_show.author,
        )
        self._append_text(
            owner,
            self._itunes_tag("email"),
            str(podcast_show.verification_email),
        )

    def _render_episode_item(
        self,
        *,
        channel: ElementTree.Element,
        podcast_show: PodcastShow,
        publication: EpisodePublication,
    ) -> None:
        item = ElementTree.SubElement(
            channel,
            "item",
        )

        self._append_text(
            item,
            "title",
            publication.title,
        )
        self._append_text(
            item,
            "description",
            publication.description,
        )

        guid = ElementTree.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "false",
            },
        )
        guid.text = publication.guid

        self._append_text(
            item,
            "pubDate",
            self._format_publication_date(
                published_at=publication.published_at,
            ),
        )

        ElementTree.SubElement(
            item,
            "enclosure",
            {
                "url": podcast_show.build_public_url(
                    object_key=publication.audio_object_key,
                ),
                "length": str(publication.audio_size_bytes),
                "type": publication.audio_content_type,
            },
        )

        self._append_text(
            item,
            self._itunes_tag("duration"),
            str(round(publication.duration_seconds)),
        )

    @staticmethod
    def _validate_episode_publications(
        *,
        podcast_show: PodcastShow,
        episode_publications: List[EpisodePublication],
    ) -> None:
        if not episode_publications:
            raise ValueError("An RSS feed must contain at least one episode publication.")

        seen_guids: Set[str] = set()
        seen_audio_object_keys: Set[str] = set()

        for publication in episode_publications:
            if publication.show_id != podcast_show.show_id:
                raise ValueError(
                    "Every episode publication rendered into an RSS feed "
                    "must belong to the target podcast show."
                )

            if publication.guid in seen_guids:
                raise ValueError(
                    "Episode publications rendered into an RSS feed "
                    "must contain unique GUID values."
                )

            if publication.audio_object_key in seen_audio_object_keys:
                raise ValueError(
                    "Episode publications rendered into an RSS feed "
                    "must contain unique audio object keys."
                )

            seen_guids.add(publication.guid)
            seen_audio_object_keys.add(publication.audio_object_key)

    @staticmethod
    def _append_text(
        parent: ElementTree.Element,
        tag: str,
        text: str,
    ) -> ElementTree.Element:
        element = ElementTree.SubElement(
            parent,
            tag,
        )
        element.text = text
        return element

    @staticmethod
    def _format_publication_date(
        *,
        published_at: datetime,
    ) -> str:
        return format_datetime(
            published_at.astimezone(timezone.utc),
            usegmt=True,
        )

    @staticmethod
    def _itunes_tag(
        name: str,
    ) -> str:
        return f"{{{ITUNES_NAMESPACE}}}{name}"

from workers import (
    WorkerEntrypoint, # type: ignore
    WorkflowEntrypoint, # type: ignore
)


WORKFLOW_BATCH_SIZE = 100


class PulsePipelineWorkflow(WorkflowEntrypoint):
    async def run(self, event, step):
        pipeline_id = event["payload"]["pipeline_id"]
        run_id = event["instanceId"]

        @step.do(
            "run-pipeline",
            config={
                "retries": {
                    "limit": 5,
                    "delay": "10 seconds",
                    "backoff": "exponential",
                },
                "timeout": "30 minutes",
            },
        )
        async def run_pipeline(ctx):
            import sys
            import traceback

            from workers.workflows import NonRetryableError  # type: ignore

            from langgraph_checkpoint_cloudflare_d1.worker import (  # type: ignore
                WorkerCloudflareD1Saver,
            )
            from pulse.application.composition.cloud import (
                CloudflareRestCredentials,
                ProviderCredentials,
                ResourceNames,
                bootstrap_cloud,
            )
            from pulse.application.execution.run_manager import (
                RunManager,
            )

            try:
                print(
                    "event=workflow_attempt_started "
                    f"run={run_id} "
                    f"pipeline={pipeline_id} "
                    f"attempt={ctx['attempt']}"
                )

                checkpointer = WorkerCloudflareD1Saver(
                    self.env.PULSE_DB,
                )

                resources = ResourceNames(
                    vectorize_index_name=(
                        self.env.PULSE_VECTORIZE_INDEX_NAME
                    ),
                    podcast_bucket_name=(
                        self.env.PULSE_PODCAST_BUCKET_NAME
                    ),
                )

                cloudflare = CloudflareRestCredentials(
                    api_token=self.env.CLOUDFLARE_API_TOKEN,
                    account_id=self.env.CLOUDFLARE_ACCOUNT_ID,
                    d1_database_id=(
                        self.env.CLOUDFLARE_D1_DATABASE_ID
                    ),
                )

                providers = ProviderCredentials(
                    anthropic_api_key=self.env.ANTHROPIC_API_KEY,
                    voyage_api_key=self.env.VOYAGE_API_KEY,
                    x_bearer_token=self.env.X_BEARER_TOKEN,
                    elevenlabs_api_key=self.env.ELEVENLABS_API_KEY,
                )

                async with bootstrap_cloud(
                    checkpointer=checkpointer,
                    resources=resources,
                    cloudflare=cloudflare,
                    providers=providers,
                    r2_bucket=_podcast_bucket(self.env),
                ) as application:
                    run_manager = RunManager(
                        application=application,
                        run_log_stream=sys.stdout,
                    )

                    state = await run_manager.run_or_resume(
                        run_id=run_id,
                        pipeline_id=pipeline_id,
                    )

                    workflow_outcome = state.get(
                        "workflow_outcome"
                    )

                    if workflow_outcome is None:
                        raise RuntimeError(
                            "Pulse workflow completed without a terminal "
                            f"outcome. Run ID: '{run_id}'. "
                            f"Pipeline ID: '{pipeline_id}'."
                        )

                    no_content_reason = state.get(
                        "no_content_reason"
                    )

                    return {
                        "run_id": state["run_id"],
                        "pipeline_id": state["pipeline_id"],
                        "episode_id": (
                            state["episode_id"]
                            if no_content_reason is None
                            else None
                        ),
                        "workflow_outcome": workflow_outcome.value,
                        "no_content_reason": (
                            no_content_reason.value
                            if no_content_reason is not None
                            else None
                        ),
                    }

            except Exception as exc:
                non_retryable = _is_non_retryable_error(exc)

                print(
                    "event=workflow_attempt_failed "
                    f"run={run_id} "
                    f"pipeline={pipeline_id} "
                    f"attempt={ctx['attempt']} "
                    f"retryable={not non_retryable} "
                    f"error_type={exc.__class__.__name__} "
                    f"error={exc}"
                )

                traceback.print_exception(exc)
                
                if _is_non_retryable_error(exc):
                    raise NonRetryableError(
                        f"Pipeline '{pipeline_id}' cannot be retried: "
                        f"{exc}"
                    ) from exc

                raise

        return await run_pipeline() # type: ignore[misc]


class Default(WorkerEntrypoint):
    async def scheduled(
        self,
        controller,
        _env,
        _ctx,
    ):
        from workers import env  # type: ignore

        from datetime import datetime, timezone
        import traceback

        from pulse.application.configuration.configuration_bootstrap import (
            bootstrap_cloud_configuration,
        )
        from pulse.application.composition.cloud import (
            CloudflareRestCredentials,
        )
        from pulse.infrastructure.cloudflare.workflow import (
            build_scheduled_workflow_id,
        )

        scheduled_at = datetime.fromtimestamp(
            controller.scheduledTime / 1000,
            tz=timezone.utc,
        )

        print(
            "event=scheduler_tick_started "
            f"scheduled_at={scheduled_at.isoformat()}"
        )

        try:
            cloudflare = CloudflareRestCredentials(
                api_token=env.CLOUDFLARE_API_TOKEN,
                account_id=env.CLOUDFLARE_ACCOUNT_ID,
                d1_database_id=env.CLOUDFLARE_D1_DATABASE_ID,
            )

            async with bootstrap_cloud_configuration(
                cloudflare=cloudflare,
            ) as application:
                due_schedules = (
                    await application.schedule_manager.list_due(
                        cutoff=scheduled_at,
                    )
                )

                print(
                    "event=scheduler_due_schedules_loaded "
                    f"scheduled_at={scheduled_at.isoformat()} "
                    f"due_count={len(due_schedules)}"
                )

                if not due_schedules:
                    print(
                        "event=scheduler_no_due_schedules "
                        f"scheduled_at={scheduled_at.isoformat()}"
                    )
                    return

                dispatched_count = 0
                advanced_count = 0
                advance_conflict_count = 0

                for start in range(
                    0,
                    len(due_schedules),
                    WORKFLOW_BATCH_SIZE,
                ):
                    schedules = due_schedules[
                        start:start + WORKFLOW_BATCH_SIZE
                    ]

                    instances = [
                        {
                            "id": build_scheduled_workflow_id(
                                pipeline_id=schedule.pipeline_id,
                                scheduled_for=schedule.next_run_at,
                            ),
                            "params": {
                                "pipeline_id": schedule.pipeline_id,
                            },
                        }
                        for schedule in schedules
                    ]

                    pipeline_ids = [
                        schedule.pipeline_id
                        for schedule in schedules
                    ]

                    print(
                        "event=scheduler_batch_dispatch_started "
                        f"scheduled_at={scheduled_at.isoformat()} "
                        f"batch_start={start} "
                        f"batch_size={len(schedules)} "
                        f"pipeline_ids={pipeline_ids}"
                    )

                    await env.PULSE_PIPELINE_WORKFLOW.create_batch(
                        instances
                    )

                    dispatched_count += len(schedules)

                    print(
                        "event=scheduler_batch_dispatch_completed "
                        f"scheduled_at={scheduled_at.isoformat()} "
                        f"batch_start={start} "
                        f"batch_size={len(schedules)}"
                    )

                    for schedule in schedules:
                        advanced = (
                            await application.schedule_manager.advance_occurrence(
                                schedule=schedule,
                                dispatched_at=scheduled_at,
                            )
                        )

                        if advanced:
                            advanced_count += 1
                            print(
                                "event=scheduler_schedule_advanced "
                                f"pipeline={schedule.pipeline_id} "
                                f"previous_next_run_at={schedule.next_run_at.isoformat()} "
                                f"scheduled_at={scheduled_at.isoformat()}"
                            )
                        else:
                            advance_conflict_count += 1
                            print(
                                "event=scheduler_schedule_advance_conflict "
                                f"pipeline={schedule.pipeline_id} "
                                f"previous_next_run_at={schedule.next_run_at.isoformat()} "
                                f"scheduled_at={scheduled_at.isoformat()}"
                            )

                print(
                    "event=scheduler_tick_completed "
                    f"scheduled_at={scheduled_at.isoformat()} "
                    f"due_count={len(due_schedules)} "
                    f"dispatched_count={dispatched_count} "
                    f"advanced_count={advanced_count} "
                    f"advance_conflict_count={advance_conflict_count}"
                )

        except Exception as exc:
            print(
                "event=scheduler_tick_failed "
                f"scheduled_at={scheduled_at.isoformat()} "
                f"error_type={exc.__class__.__name__} "
                f"error={exc}"
            )
            traceback.print_exception(exc)
            raise


def _podcast_bucket(env: object) -> object | None:
    try:
        bucket = getattr(env, "PULSE_PODCAST_BUCKET")  # noqa: B009
    except Exception:
        return None

    if not bucket:
        return None

    return bucket


def _is_non_retryable_error(
    error: BaseException,
) -> bool:
    from typing import Optional
    from pulse.application.execution.errors import (
        NonRetryableWorkflowError,
    )

    current: Optional[BaseException] = error

    while current is not None:
        if isinstance(
            current,
            NonRetryableWorkflowError,
        ):
            return True

        current = current.__cause__

    return False
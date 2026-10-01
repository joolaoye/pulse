import asyncio
import json
import os
from pathlib import (
    Path,
)
import shutil
import tempfile


class WranglerRunner:
    def __init__(
        self,
        *,
        cloudflare_account_id: str,
        cloudflare_api_token: str,
        working_directory: Path = Path("."),
    ) -> None:
        self.cloudflare_account_id = cloudflare_account_id

        self.cloudflare_api_token = cloudflare_api_token

        self.working_directory = working_directory.resolve()

    async def apply_d1_migrations(
        self,
        *,
        database_name: str,
        database_id: str,
    ) -> None:
        config_path = self._create_d1_migration_config(
            database_name=(database_name),
            database_id=(database_id),
        )

        try:
            await self._run_d1_migrations(
                database_name=(database_name),
                config_path=(config_path),
            )

        finally:
            config_path.unlink(
                missing_ok=True,
            )

    def _resolve_wrangler_executable(
        self,
    ) -> str:
        binary_directory = self.working_directory / "node_modules" / ".bin"

        wrangler_executable = shutil.which(
            "wrangler",
            path=str(binary_directory),
        )

        if wrangler_executable is None:
            raise RuntimeError(
                (
                    "The project-local Wrangler "
                    "installation could not be found. "
                    "Run './bootstrap' before "
                    "running 'pulse init'."
                )
            )

        return wrangler_executable

    def _create_d1_migration_config(
        self,
        *,
        database_name: str,
        database_id: str,
    ) -> Path:
        config = {
            "d1_databases": [
                {
                    "binding": ("PULSE_DB"),
                    "database_name": (database_name),
                    "database_id": (database_id),
                    "migrations_dir": ("migrations/d1"),
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=".pulse-init-",
            dir=self.working_directory,
            delete=False,
            encoding="utf-8",
        ) as file:
            json.dump(
                config,
                file,
            )

            return Path(file.name)

    async def _run_d1_migrations(
        self,
        *,
        database_name: str,
        config_path: Path,
    ) -> None:
        wrangler_executable = self._resolve_wrangler_executable()

        environment = dict(os.environ)

        environment["CLOUDFLARE_ACCOUNT_ID"] = self.cloudflare_account_id

        environment["PULSE_CLOUDFLARE_API_TOKEN"] = self.cloudflare_api_token

        process = await asyncio.create_subprocess_exec(
            wrangler_executable,
            "d1",
            "migrations",
            "apply",
            database_name,
            "--remote",
            "--config",
            str(config_path),
            cwd=str(self.working_directory),
            env=environment,
            stdin=(asyncio.subprocess.DEVNULL),
            stdout=(asyncio.subprocess.PIPE),
            stderr=(asyncio.subprocess.PIPE),
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return

        stdout_text = stdout.decode(
            "utf-8",
            errors="replace",
        )

        stderr_text = stderr.decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError((f"Failed to apply D1 migrations.\n{stdout_text}\n{stderr_text}"))

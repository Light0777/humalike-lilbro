from pathlib import Path

from loguru import logger


class MigrationRunner:
    def __init__(self, supabase_url: str, service_key: str) -> None:
        self._url = supabase_url
        self._key = service_key
        self._migrations_dir = Path(__file__).parent / "migrations"

    def list_pending(self) -> list[str]:
        sql_files = sorted(self._migrations_dir.glob("*.sql"))
        return [f.name for f in sql_files]

    def print_sql(self, migration_name: str) -> str:
        path = self._migrations_dir / migration_name
        if not path.exists():
            raise FileNotFoundError(f"Migration not found: {migration_name}")
        return path.read_text(encoding="utf-8")

    def print_all(self) -> None:
        for name in self.list_pending():
            print(f"\n{'='*60}")
            print(f"  Migration: {name}")
            print(f"{'='*60}\n")
            print(self.print_sql(name))
            print()

    async def run_all(self) -> None:
        if not self._key:
            logger.warning(
                "SUPABASE_SERVICE_KEY not set. "
                "Run migrations manually via Supabase dashboard or run: "
                "python -c 'from gaming_ai.database.migration_runner import MigrationRunner; "
                "MigrationRunner(\"<url>\", \"<key>\").print_all()'"
            )
            return

        import httpx

        headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

        for name in self.list_pending():
            sql = self.print_sql(name)
            logger.info("Applying migration: {}", name)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._url}/rest/v1/sql",
                    headers=headers,
                    json={"query": sql},
                )

                if response.status_code == 200:
                    logger.info("Applied migration: {}", name)
                elif response.status_code == 404:
                    logger.warning(
                        "SQL endpoint not available (404). "
                        "Apply {} manually via Supabase dashboard.", name
                    )
                else:
                    logger.error(
                        "Migration {} failed: {} {}",
                        name, response.status_code, response.text,
                    )
                    raise RuntimeError(f"Migration {name} failed")

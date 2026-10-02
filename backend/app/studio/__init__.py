"""Local client projects, rights records, and repeatable download workflows."""


def initialize(conn):
    """Add studio tables without rewriting an existing media library."""
    statements = (
        """CREATE TABLE IF NOT EXISTS studio_projects (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT NOT NULL DEFAULT '',
            budget_cents INTEGER NOT NULL DEFAULT 0 CHECK(budget_cents >= 0), due_at TEXT,
            notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','active','delivered')),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS studio_project_items (
            project_id TEXT NOT NULL REFERENCES studio_projects(id) ON DELETE CASCADE,
            task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            PRIMARY KEY(project_id, task_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_studio_items_task ON studio_project_items(task_id)",
        """CREATE TABLE IF NOT EXISTS studio_rights (
            task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
            license TEXT NOT NULL DEFAULT 'unknown'
                CHECK(license IN ('unknown','owned','cc0','cc-by','permission')),
            attribution TEXT NOT NULL DEFAULT '', evidence_url TEXT NOT NULL DEFAULT '',
            verified INTEGER NOT NULL DEFAULT 0 CHECK(verified IN (0,1)), updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS studio_workflows (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            preset TEXT NOT NULL, collection_id TEXT REFERENCES collections(id) ON DELETE SET NULL,
            tags TEXT NOT NULL DEFAULT '[]', rate_limit INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS studio_activity (
            id TEXT PRIMARY KEY, action TEXT NOT NULL, entity_id TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_studio_activity_time ON studio_activity(created_at DESC)",
    )
    for statement in statements:
        conn.execute(statement)

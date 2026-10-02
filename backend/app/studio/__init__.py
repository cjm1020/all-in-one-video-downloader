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
        """CREATE TRIGGER IF NOT EXISTS studio_reopen_removed_item AFTER DELETE ON studio_project_items
        BEGIN
            INSERT INTO studio_activity SELECT lower(hex(randomblob(16))),'project.reopened',id,
                '{"reason":"media_removed"}',strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                FROM studio_projects WHERE id=OLD.project_id AND status='delivered';
            UPDATE studio_projects SET status='active',updated_at=strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                WHERE id=OLD.project_id AND status='delivered';
        END""",
        """CREATE TRIGGER IF NOT EXISTS studio_reopen_task_status AFTER UPDATE OF status ON tasks
        WHEN NEW.status != 'completed'
        BEGIN
            INSERT INTO studio_activity SELECT lower(hex(randomblob(16))),'project.reopened',id,
                '{"reason":"media_status_changed"}',strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                FROM studio_projects WHERE status='delivered' AND id IN
                (SELECT project_id FROM studio_project_items WHERE task_id=NEW.id);
            UPDATE studio_projects SET status='active',updated_at=strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                WHERE status='delivered' AND id IN
                (SELECT project_id FROM studio_project_items WHERE task_id=NEW.id);
        END""",
        """CREATE TRIGGER IF NOT EXISTS studio_reopen_rights AFTER UPDATE ON studio_rights
        WHEN NEW.verified=0 OR NEW.license='unknown' OR (NEW.license='cc-by' AND trim(NEW.attribution)='')
            OR (NEW.license='permission' AND trim(NEW.evidence_url)='')
        BEGIN
            INSERT INTO studio_activity SELECT lower(hex(randomblob(16))),'project.reopened',id,
                '{"reason":"rights_changed"}',strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                FROM studio_projects WHERE status='delivered' AND id IN
                (SELECT project_id FROM studio_project_items WHERE task_id=NEW.task_id);
            UPDATE studio_projects SET status='active',updated_at=strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
                WHERE status='delivered' AND id IN
                (SELECT project_id FROM studio_project_items WHERE task_id=NEW.task_id);
        END""",
    )
    for statement in statements:
        conn.execute(statement)

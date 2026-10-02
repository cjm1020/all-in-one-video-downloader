from app import db


def test_studio_initialization_is_additive_and_idempotent(client, task):
    db.initialize()
    db.initialize()
    assert db.get_task(task["id"])["url"] == task["url"]
    with db.connection() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"studio_projects", "studio_project_items", "studio_rights", "studio_workflows"} <= tables


def test_studio_relationships_cascade_without_deleting_media(client, task):
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO studio_projects(id,name,created_at,updated_at) VALUES (?,?,?,?)",
            ("project", "客户项目", db.now(), db.now()),
        )
        conn.execute("INSERT INTO studio_project_items VALUES (?,?)", ("project", task["id"]))
        conn.execute("DELETE FROM studio_projects WHERE id='project'")
        assert conn.execute("SELECT COUNT(*) FROM studio_project_items").fetchone()[0] == 0
    assert db.get_task(task["id"])

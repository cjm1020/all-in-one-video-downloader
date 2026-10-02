import json

from .. import db


def summary() -> dict:
    """Aggregate local operational data; budget is planned work, not revenue."""
    with db.connection() as conn:
        conn.execute("BEGIN")
        projects = conn.execute(
            """SELECT COUNT(*) AS projects, COALESCE(SUM(status='active'),0) AS active_projects,
            COALESCE(SUM(status='delivered'),0) AS delivered_projects,
            COALESCE(SUM(budget_cents),0) AS budget_cents FROM studio_projects"""
        ).fetchone()
        media = conn.execute(
            """SELECT COUNT(*) AS completed_media, COALESCE(SUM(MAX(t.file_size,0)),0) AS storage_bytes,
            COALESCE(SUM(MAX(t.duration,0)),0)/60.0 AS download_minutes,
            COALESCE(SUM(r.verified=1 AND r.license!='unknown'
                AND (r.license!='cc-by' OR trim(r.attribution)!='')
                AND (r.license!='permission' OR trim(r.evidence_url)!='')),0) AS licensed_media
            FROM tasks t LEFT JOIN studio_rights r ON r.task_id=t.id WHERE t.status='completed'"""
        ).fetchone()
        platforms = [
            {"name": row["name"], "count": row["count"]}
            for row in conn.execute(
                """SELECT COALESCE(NULLIF(platform,''),'未知平台') AS name,COUNT(*) AS count
            FROM tasks WHERE status='completed' GROUP BY name ORDER BY count DESC,name LIMIT 20"""
            )
        ]
        activity = []
        for row in conn.execute("SELECT * FROM studio_activity ORDER BY created_at DESC,id DESC LIMIT 30"):
            event = dict(row)
            event["details"] = json.loads(event["details"])
            activity.append(event)
        return {**dict(projects), **dict(media), "platforms": platforms, "activity": activity}

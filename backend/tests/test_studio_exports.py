import csv
import io

from app import db


def test_export_preview_documents_incomplete_project_and_rights(client, task):
    project = client.post("/api/studio/projects", json={"name": "研究项目", "notes": "客户需求"}).json()
    endpoint = f"/api/studio/projects/{project['id']}"
    client.put(endpoint + "/items", json={"task_ids": [task["id"]]})
    json_response = client.get(endpoint + "/export?format=json")
    manifest = json_response.json()
    assert json_response.status_code == 200
    assert manifest["schema_version"] == 1
    assert manifest["project"]["notes"] == "客户需求"
    assert not manifest["checklist"]["ready"]
    assert manifest["items"][0]["rights"]["license"] == "unknown"
    assert "file_path" not in json_response.text and "lease_at" not in json_response.text
    markdown = client.get(endpoint + "/export?format=markdown")
    assert "可以交付：否" in markdown.text and "待处理项" in markdown.text
    assert markdown.headers["content-disposition"].endswith('.md"')
    assert client.get(endpoint + "/export?format=xml").status_code == 400


def test_csv_quotes_fields_and_neutralizes_spreadsheet_formulas(client, task):
    project = client.post("/api/studio/projects", json={"name": "表格交付"}).json()
    endpoint = f"/api/studio/projects/{project['id']}"
    client.put(endpoint + "/items", json={"task_ids": [task["id"]]})
    db.update_task(task["id"], {"title": '=HYPERLINK("https://example.com","open")', "tags": ["a,b", "中文"]})
    response = client.get(endpoint + "/export?format=csv")
    reader = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert reader[0]["title"].startswith("'=HYPERLINK")
    assert reader[0]["tags"] == "a,b, 中文"
    assert response.headers["content-type"].startswith("text/csv")

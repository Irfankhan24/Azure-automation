import requests
import json
import os

ORG_NAME = "rapyuta-robotics"
PROJECT_NAME = "Oks"
PAT = "F6cNWrSCzxRPRmc0JQnIZrqVq0bM5g9JczrH3TCdmRY4X5KkihRdJQQJ99BDACAAAAA1kgrNAAASAZDO1CWe"
HEADERS = {
    "Content-Type": "application/json-patch+json",
    "Accept": "application/json"
}
AUTH = ("", PAT)
QUERY_URL = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/wiql?api-version=7.0"

query_payload = {
    "query": f"""
        SELECT [System.Id] FROM WorkItems
        WHERE [System.WorkItemType] = 'Maintenance Story' AND [System.TeamProject] = '{PROJECT_NAME}'
    """
}

query_resp = requests.post(QUERY_URL, headers={"Content-Type": "application/json"}, auth=AUTH, json=query_payload)

if query_resp.status_code != 200:
    print("Error fetching work items:", query_resp.status_code, query_resp.text)
    exit()

work_items = query_resp.json().get("workItems", [])
print(f"Found {len(work_items)} maintenance stories.")

for item in work_items:
    work_item_id = item["id"]
    work_item_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?$expand=relations&api-version=7.0"
    work_item_resp = requests.get(work_item_url, headers=HEADERS, auth=AUTH)

    if work_item_resp.status_code == 200:
        work_item_data = work_item_resp.json()
        issueCount = 0

        if "relations" in work_item_data:
            for relation in work_item_data["relations"]:
                if relation['rel'] in ['ArtifactLink', 'AttachedFile']:
                    continue

                url = relation['url']
                response = requests.get(url, headers=HEADERS, auth=AUTH)
                data = response.json()

                if response.status_code == 200 and data['fields'].get('System.WorkItemType') == 'Issue':
                    issueCount += 1

        update_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
        update_data = [
            {
                "op": "replace",  
                "path": "/fields/Custom.IssueInstancesCount",
                "value": issueCount
            }
        ]

        update_resp = requests.patch(update_url, json=update_data, headers=HEADERS, auth=AUTH)

        if update_resp.status_code in [200, 201]:
            print(f"Updated Work Item {work_item_id} with IssueInstancesCount = {issueCount}")
        else:
            print(f"Failed to update Work Item {work_item_id}. Status: {update_resp.status_code}, Error: {update_resp.text}")
    else:
        print(f"Failed to fetch Work Item {work_item_id}. Status: {work_item_resp.status_code}")

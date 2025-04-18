import requests
import time

# Authentication and project details
QUERY_ID = "5627f7af-2ca2-460e-975f-68dc28041fdd"
HEADERS = {"Content-Type": "application/json"}
ORG_NAME = "rapyuta-robotics"
PROJECT_NAME = "Oks"
PAT = "6ZQLtnOq"
AUTH = ("", PAT)

UPDATE_HEADERS = {
    "Content-Type": "application/json-patch+json",
    "Accept": "application/json"
}

SAVE_FILE_LOCALLY = False
UPDATE_DATABASE = True

# Prepare query
QUERY_URL = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/wiql?api-version=7.0"
query_payload = {
    "query": f"""
        SELECT [System.Id] FROM WorkItems
        WHERE [System.TeamProject] = '{PROJECT_NAME}' 
        AND [System.WorkItemType] = 'Issue' 
        AND [System.CreatedDate] > @StartOfYear
    """
}

response = requests.post(QUERY_URL, headers=HEADERS, auth=AUTH, json=query_payload)

if response.status_code == 200: 

    work_items = response.json().get("workItems", [])
    print(f"🔍 Found {len(work_items)} work items.")
    i=0
    for item in work_items:
        work_item_id = item["id"]
        work_item_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?$expand=relations&api-version=7.0"
        
        try:
            work_item_resp = requests.get(work_item_url, headers=HEADERS, auth=AUTH) 
            if i==0: 
                print(work_item_resp.json()) 
                i=i+1
            if work_item_resp.status_code != 200:
                print(f" Failed to fetch Work Item {work_item_id}. Status: {work_item_resp.status_code}")
                continue

            work_item_data = work_item_resp.json()
            attachment_found = False

            if "relations" in work_item_data:
                for relation in work_item_data["relations"]:
                    if relation.get("rel") == "AttachedFile" and relation.get("attributes", {}).get("name") == "version.txt":
                        attachment_found = True
                        attachment_url = relation["url"]
                        attachment_id = attachment_url.split("/")[-1].split("?")[0]

                        # Download version.txt
                        download_url = f"https://dev.azure.com/{ORG_NAME}/_apis/wit/attachments/{attachment_id}?api-version=7.1"
                        download_resp = requests.get(download_url, headers=HEADERS, auth=AUTH)

                        if download_resp.status_code == 200:
                            file_content = download_resp.text
                            print(f" Processing version.txt for Work Item {work_item_id}")

                            oks_server_version = None
                            for line in file_content.splitlines():
                                if line.startswith("oks_server"):
                                    oks_server_version = line.split()[-1]
                                    break

                            if oks_server_version:
                                print(f" Extracted oks_server version: {oks_server_version}")

                                if UPDATE_DATABASE:
                                    update_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
                                    update_data = [
                                        {
                                            "op": "add",
                                            "path": "/fields/Custom.Foundrr_oksVersion",
                                            "value": oks_server_version
                                        }
                                    ]

                                    for attempt in range(2):  # add → replace fallback
                                        try:
                                            update_resp = requests.patch(update_url, json=update_data, headers=UPDATE_HEADERS, auth=AUTH, timeout=10)
                                            if update_resp.status_code in [200, 201]:
                                                print(f"✅ Updated Work Item {work_item_id} with oks_server version: {oks_server_version}")
                                                break
                                            elif attempt == 0:
                                                print(f"'add' failed, trying 'replace'...")
                                                update_data[0]["op"] = "replace"
                                            else:
                                                print(f"Failed to update Work Item {work_item_id}. Status: {update_resp.status_code}, Error: {update_resp.text}")
                                        except requests.exceptions.RequestException as e:
                                            print(f"Connection error while updating Work Item {work_item_id}: {e}")
                                            time.sleep(2)
                            else:
                                print(f"oks_server' not found in version.txt for Work Item {work_item_id}")
                        else:
                            print(f"Failed to download attachment. Status: {download_resp.status_code}")
                if not attachment_found:
                    print(f"No version.txt found for Work Item {work_item_id}")
        except requests.exceptions.RequestException as err:
            print(f"Connection error fetching Work Item {work_item_id}: {err}")
else:
    print(f"❌ Failed to fetch work items. Status: {response.status_code}, Error: {response.text}")

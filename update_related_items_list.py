import requests

# Azure DevOps Config
ORG_NAME = "rapyuta-robotics"
PROJECT_NAME = "Oks"
PAT = "F6cNWrSCzxRPRmc0JQnIZrqVq0bM5g9JczrH3TCdmRY4X5KkihRdJQQJ99BDACAAAAA1kgrNAAASAZDO1CWe"  # Replace with your PAT
AUTH = ("", PAT)

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Field configurations
FIELDS_TO_UPDATE = {
    'Related': 'Custom.RelatedWorkItemsList',
    'Predecessor': 'Custom.PredecessorsWorkItemsList',
    'Successor': 'Custom.SuccessorsWorkItemsList'
}

def categorize_relations(relations):
    """Simple relation categorization"""
    categorized = {k: [] for k in FIELDS_TO_UPDATE.keys()}
    
    for relation in relations:
        # rel_type = relation.get('rel', '')
        # rel_type = relation.get('rel')
        if relation['rel'] in ['ArtifactLink', 'AttachedFile']:
            continue
            
        related_id = relation['url'].split('/')[-1]
        

        if relation['attributes']['name'] == 'Predecessor':
            categorized['Predecessor'].append(related_id)
        elif relation['attributes']['name'] == 'Successor':
            categorized['Successor'].append(related_id)
        
        categorized['Related'].append(related_id)
    
    return categorized

# Fetch work items
QUERY_URL = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/wiql?api-version=7.0"
query_payload = {
    "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Maintenance Story' AND [System.TeamProject] = '{PROJECT_NAME}'"
}

work_items = requests.post(QUERY_URL, headers=HEADERS, auth=AUTH, json=query_payload).json().get("workItems", [])
print(f"Found {len(work_items)} maintenance stories.")

for item in work_items:
    work_item_id = item["id"]
    print(f"\nProcessing Work Item ID: {work_item_id}")

    # Get work item details
    work_item_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?$expand=relations&api-version=7.0"
    relations = requests.get(work_item_url, headers=HEADERS, auth=AUTH).json().get("relations", [])
    
    # Categorize relations
    categorized = categorize_relations(relations)
    
    # Prepare updates
    update_operations = []
    for rel_type, field_name in FIELDS_TO_UPDATE.items():
        ids = categorized[rel_type]
        if ids:
            # Your original simple approach - take all available items
            value = ", ".join(ids)
            update_operations.append({
                "op": "replace",
                "path": f"/fields/{field_name}",
                "value": value
            })
            print(f"{rel_type} IDs: {value}")

    # Execute update if we have operations
    if update_operations:
        update_url = f"https://dev.azure.com/{ORG_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{work_item_id}?api-version=7.0"
        update_headers = {
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }
        
        response = requests.patch(update_url, json=update_operations, headers=update_headers, auth=AUTH)
        
        if response.status_code in [200, 201]:
            print(f"Updated work item {work_item_id}")
        else:
            print(f"Failed to update {work_item_id}: {response.status_code} - {response.text}")
    else:
        print("No relations to update")



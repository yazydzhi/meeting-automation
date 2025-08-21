curl -X POST "https://api.notion.com/v1/databases" \
  -H "Authorization: Bearer '"$NOTION_TOKEN"'" \
  -H "Content-Type: application/json" \
  -H "Notion-Version: 2022-06-28" \
  -d '{
    "parent": { "type": "page_id", "page_id": "256db316e99f809db875d78b77dcaf33" },
    "title": [
      {
        "type": "text",
        "text": { "content": "Meeting Notes" }
      }
    ],
    "properties": {
      "Name": {
        "title": {}
      },
      "Date": {
        "date": {}
      },
      "Calendar": {
        "select": {
          "options": [
            { "name": "Work", "color": "blue" },
            { "name": "Personal", "color": "green" }
          ]
        }
      },
      "Attendees": {
        "rich_text": {}
      },
      "Meeting Link": {
        "url": {}
      },
      "Drive Folder": {
        "url": {}
      },
      "Event ID": {
        "rich_text": {}
      }
    }
  }' 
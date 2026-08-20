### {{title}}

![model](https://img.shields.io/badge/model-{{model_badge}}-blue)
{{#categories}}![cat](https://img.shields.io/badge/{{.}}-lightgrey) {{/categories}}

**Prompt:**

```text
{{prompt}}
```

{{#media.video_url}}
**Preview:** {{media.video_url}}
{{/media.video_url}}

| Field | Value |
|-------|-------|
| Model | `{{model}}` |
| Author | {{author_line}} |
| Source | [Original post]({{source.url}}) |
| Engagement | {{engagement_line}} |
| Collected | {{collected_at}} |
| Tags | {{tags_line}} |

{{#notes}}
> Note: {{notes}}
{{/notes}}

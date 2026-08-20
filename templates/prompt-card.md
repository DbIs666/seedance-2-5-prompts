### {{title}}

![model](https://img.shields.io/badge/Seedance-{{model_short}}-0ea5e9)
![lang](https://img.shields.io/badge/lang-{{language}}-blue)
{{#featured}}![Featured](https://img.shields.io/badge/⭐-Featured-gold){{/featured}}

`{{id}}` · `{{model}}` · {{categories_line}}

#### Prompt

```text
{{prompt}}
```

#### Video

<div align="center">

{{#media.thumb_url}}
<a href="{{media_href}}">
<img src="{{media.thumb_url}}" width="680" alt="{{title}}" style="border-radius:12px;max-width:100%;">
</a>

{{#media.video_url}}**[▶ Watch video]({{media.video_url}})** · {{/media.video_url}}**[↗ View on X]({{source.url}})**
{{/media.thumb_url}}

{{^media.thumb_url}}
**[↗ Watch / discuss on X]({{source.url}})**
{{/media.thumb_url}}

</div>

#### Details

- **Author:** [{{author.name}}]({{author.profile_url}}) ([{{author.x_handle}}]({{author.profile_url}}))
- **Source:** [X Post]({{source.url}})
- **Published:** {{source.posted_at_human}}
- **Engagement:** ❤ {{source.likes}} · 🔁 {{source.reposts}} · 👁 {{source.views}}
- **ID:** [`{{id}}`]({{json_path}})
- **Tags:** {{tags_line}}

{{#notes}}
- **Notes:** {{notes}}
{{/notes}}

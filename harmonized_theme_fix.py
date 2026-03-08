import os

template_path = 'core/templates/core/agent_profile.html'
input_css_path = 'static/css/input.css'
safelist_path = 'core/templates/core/tailwind_safelist.html'

# 1. Update output.css link for cache busting (using timestamp)
with open(template_path, 'r') as f:
    content = f.read()

# Replace existing link with one containing a dynamic timestamp for cache busting
import re
new_link = '<link rel="stylesheet" href="{% static \'css/output.css\' %}?v={% now \'U\' %}">'
content = re.sub(r'<link rel="stylesheet" href="{% static \'css/output.css\' %}.*?>', new_link, content)

# 2. Harmonize CSS variable names in :root
root_block = """        :root {
            --theme-page: {{ theme.bg_page|default:"#ffffff" }};
            --theme-card: {{ theme.bg_card|default:"#ffffff" }};
            --theme-secondary: {{ theme.bg_secondary|default:"#f8fafc" }};
            --theme-main: {{ theme.text_main|default:"#0f172a" }};
            --theme-muted: {{ theme.text_muted|default:"#64748b" }};
            --theme-accent: {{ theme.accent|default:"#0f172a" }};
            --hero-start: {{ theme.hero_start|default:"#0f172a" }};
            --hero-end: {{ theme.hero_end|default:"#1e293b" }};
            --font-heading: {{ theme.font_heading|safe }};
            --font-body: {{ theme.font_body|safe }};
        }"""

start_marker = ':root {'
end_marker = '}'
start_idx = content.find(start_marker)
if start_idx != -1:
    end_idx = content.find(end_marker, start_idx)
    if end_idx != -1:
        content = content[:start_idx] + root_block + content[end_idx+1:]

with open(template_path, 'w') as f:
    f.write(content)

# 3. Update input.css to match harmonized variables
input_css_content = """@import "tailwindcss";
@source "../../core/templates";

@theme {
  --color-theme-page: var(--theme-page);
  --color-theme-card: var(--theme-card);
  --color-theme-secondary: var(--theme-secondary);
  --color-theme-main: var(--theme-main);
  --color-theme-muted: var(--theme-muted);
  --color-theme-accent: var(--theme-accent);
}
"""
with open(input_css_path, 'w') as f:
    f.write(input_css_content)

# 4. Update safelist for consistency
safelist_content = """<!-- Tailwind Safelist for Standard Themes -->
<div class="
    bg-theme-page text-theme-page border-theme-page
    bg-theme-card text-theme-card border-theme-card
    bg-theme-secondary text-theme-secondary border-theme-secondary
    bg-theme-main text-theme-main border-theme-main
    bg-theme-muted text-theme-muted border-theme-muted
    bg-theme-accent text-theme-accent border-theme-accent
"></div>
"""
with open(safelist_path, 'w') as f:
    f.write(safelist_content)

print("Harmonization script executed successfully.")

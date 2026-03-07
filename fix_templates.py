import os
import re

template_dir = 'core/templates/themes'

# Match {% tagname ... \n ... %}
broken_tag_pattern = re.compile(r'\{%([^%]+)\n([^%]+)%\}')

for root, _, files in os.walk(template_dir):
    for filename in files:
        if filename.endswith('.html'):
            filepath = os.path.join(root, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Replace inner newlines within {% ... %}
            def replacer(match):
                inner_content = match.group(1) + match.group(2)
                # remove any newlines and extra spaces
                inner_content = inner_content.replace('\n', ' ')
                inner_content = re.sub(r'\s+', ' ', inner_content)
                return '{%' + inner_content + '%}'
                
            new_content = broken_tag_pattern.sub(replacer, content)
            
            if new_content != content:
                print(f"Fixed broken tags in {filepath}")
                with open(filepath, 'w') as f:
                    f.write(new_content)

print("Done fixing templates.")

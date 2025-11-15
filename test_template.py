#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings
from django.template.loader import get_template
from django.template import Template, TemplateSyntaxError

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

# Test basic navbar template rendering
template_content = '''
{% if True %}
<div class="test">
    <span class="me-2">Test</span>
</div>
{% endif %}
'''

try:
    template = Template(template_content)
    rendered = template.render({})
    print('✅ Template rendering works')
    print(rendered)
except TemplateSyntaxError as e:
    print(f'❌ Template syntax error: {e}')
except Exception as e:
    print(f'❌ Other error: {e}')

# Now test the actual base.html
try:
    template = get_template('base.html')
    print('✅ base.html template loads successfully')
except Exception as e:
    print(f'❌ Error loading base.html: {e}')

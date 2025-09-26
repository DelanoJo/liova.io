#!/usr/bin/env python3
"""
Simple static file server for Jekyll site when bundle install fails.
Processes Jekyll front matter and serves static HTML files.
"""

import os
import re
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

class JekyllStaticHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, site_config=None, **kwargs):
        self.site_config = site_config or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Handle root path
        if self.path == '/':
            self.path = '/index.html'

        # Remove .html extension if not present for pretty URLs
        if not self.path.endswith('.html') and not self.path.endswith('.css') and '.' not in os.path.basename(self.path):
            self.path = self.path + '.html'

        # Try to serve the processed file
        try:
            file_path = self.translate_path(self.path)
            if os.path.isfile(file_path) and file_path.endswith('.html'):
                self.serve_processed_html(file_path)
            else:
                super().do_GET()
        except Exception as e:
            print(f"Error serving {self.path}: {e}")
            super().do_GET()

    def serve_processed_html(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process Jekyll front matter and templating
            processed_content = self.process_jekyll_content(content, file_path)

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-length', len(processed_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(processed_content.encode('utf-8'))

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            super().do_GET()

    def process_jekyll_content(self, content, file_path):
        # Extract front matter
        front_matter = {}
        if content.startswith('---'):
            try:
                _, fm_content, body = content.split('---', 2)
                # Simple YAML parsing for basic key: value pairs
                for line in fm_content.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        front_matter[key.strip()] = value.strip()
                content = body.strip()
            except:
                pass

        # If this has a layout, wrap it
        if 'layout' in front_matter:
            layout_path = os.path.join(os.path.dirname(file_path), '_layouts', front_matter['layout'] + '.html')
            if os.path.exists(layout_path):
                with open(layout_path, 'r', encoding='utf-8') as f:
                    layout_content = f.read()

                # Replace template variables
                layout_content = layout_content.replace('{{ content }}', content)

                # Process template variables
                page_title = front_matter.get('title', self.site_config.get('title', 'Delano Johnson'))
                layout_content = self.process_template_vars(layout_content, {
                    'page.title': page_title,
                    'site.title': self.site_config.get('title', 'Delano Johnson - Salesforce Technical Architect'),
                    'site.description': self.site_config.get('description', 'Salesforce Technical Architect & Data Strategist'),
                })

                content = layout_content

        return content

    def process_template_vars(self, content, variables):
        # Fix asset URLs first (before removing Jekyll syntax)
        content = content.replace("{{ '/assets/css/style.css?v=' | append: site.github.build_revision | relative_url }}",
                                '/assets/css/style.css')
        content = content.replace("{{ '/assets/css/custom.css' | relative_url }}", '/assets/css/custom.css')

        # Process Jekyll template variables
        for var, value in variables.items():
            # Handle {% if %} statements
            content = re.sub(r'\{\% if ' + var + r' \%\}.*?\{\% endif \%\}', value if value else '', content, flags=re.DOTALL)

            # Handle {{ }} variables
            content = content.replace('{{ ' + var + ' }}', value or '')

        # Remove remaining Jekyll syntax
        content = re.sub(r'\{\%.*?\%\}', '', content)
        content = re.sub(r'\{\{.*?\}\}', '', content)

        return content

def create_simple_css():
    """Create a simple style.css if it doesn't exist"""
    css_dir = Path('/Users/delanojohnson/liova.io/assets/css')
    style_css_path = css_dir / 'style.css'

    if not style_css_path.exists():
        # Create a minimal base CSS that mimics the Cayman theme
        base_css = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }

        .main-content {
            max-width: 64rem;
            margin: 0 auto;
            padding: 2rem;
        }

        .page-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
        }

        nav a {
            color: white;
            text-decoration: none;
            margin: 0 1rem;
        }

        nav a:hover {
            text-decoration: underline;
        }
        """

        with open(style_css_path, 'w') as f:
            f.write(base_css)
        print(f"Created basic style.css at {style_css_path}")

def start_server():
    """Start the static file server"""
    os.chdir('/Users/delanojohnson/liova.io')

    # Create basic CSS if needed
    create_simple_css()

    # Site configuration
    site_config = {
        'title': 'Delano Johnson - Salesforce Technical Architect',
        'description': 'Salesforce Technical Architect & Data Strategist with 12+ years building enterprise solutions'
    }

    PORT = 8000

    # Create custom handler with site config
    def handler_factory(*args, **kwargs):
        return JekyllStaticHandler(*args, site_config=site_config, **kwargs)

    with socketserver.TCPServer(("", PORT), handler_factory) as httpd:
        print(f"🚀 Local server running at: http://localhost:{PORT}")
        print(f"📁 Serving from: {os.getcwd()}")
        print("\n📖 Available pages:")
        print(f"   • Homepage: http://localhost:{PORT}")
        print(f"   • About: http://localhost:{PORT}/about")
        print(f"   • Experience: http://localhost:{PORT}/experience")
        print(f"   • Certifications: http://localhost:{PORT}/certifications")
        print("\n⏹️  Press Ctrl+C to stop the server")

        # Open browser automatically
        def open_browser():
            webbrowser.open(f'http://localhost:{PORT}')

        browser_thread = threading.Timer(1.0, open_browser)
        browser_thread.start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped.")

if __name__ == "__main__":
    start_server()
"""Application landing page."""

import re
from typing import Annotated

import markdown
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from configuration.application import ApplicationSettings

router = APIRouter()


def prepare_mermaid_blocks(rendered_markdown: str) -> str:
    """Convert Mermaid code blocks into elements processed by Mermaid.js."""
    return re.sub(
        pattern=(
            r'<pre><code class="language-mermaid">'
            r"(.*?)"
            r"</code></pre>"
        ),
        repl=r'<pre class="mermaid">\1</pre>',
        string=rendered_markdown,
        flags=re.DOTALL,
    )


@router.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def read_readme(
    settings: Annotated[
        ApplicationSettings,
        Depends(ApplicationSettings.get_settings),
    ],
) -> HTMLResponse:
    """Render the project README as the application landing page."""
    readme_path = settings.project_root / "README.md"
    markdown_text = readme_path.read_text(encoding="utf-8")

    rendered_markdown = markdown.markdown(
        markdown_text,
        extensions=[
            "fenced_code",
            "tables",
        ],
    )

    rendered_markdown = prepare_mermaid_blocks(rendered_markdown)

    html_document = f"""
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1"
            >
            <title>{settings.app_name}</title>

            <script type="module">
                import mermaid from
                    "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

                mermaid.initialize({{
                    startOnLoad: true,
                    securityLevel: "strict",
                    theme: "default"
                }});
            </script>

            <style>
                body {{
                    max-width: 900px;
                    margin: 40px auto;
                    padding: 0 24px;
                    font-family:
                        Arial,
                        Helvetica,
                        sans-serif;
                    line-height: 1.6;
                    color: #24292f;
                }}

                h1,
                h2,
                h3,
                h4 {{
                    margin-top: 1.5em;
                    margin-bottom: 0.5em;
                    line-height: 1.25;
                }}

                h1,
                h2 {{
                    padding-bottom: 0.3em;
                    border-bottom: 1px solid #d0d7de;
                }}

                a {{
                    color: #0969da;
                }}

                code {{
                    padding: 2px 5px;
                    background: #f6f8fa;
                    border-radius: 4px;
                    font-family:
                        Consolas,
                        "Courier New",
                        monospace;
                }}

                pre {{
                    overflow-x: auto;
                    padding: 16px;
                    background: #f6f8fa;
                    border-radius: 6px;
                }}

                pre code {{
                    padding: 0;
                    background: transparent;
                }}

                pre.mermaid {{
                    display: flex;
                    justify-content: center;
                    background: transparent;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th,
                td {{
                    padding: 8px 12px;
                    border: 1px solid #d0d7de;
                    text-align: left;
                }}

                th {{
                    background: #f6f8fa;
                }}

                img {{
                    max-width: 100%;
                }}

                blockquote {{
                    margin-left: 0;
                    padding-left: 16px;
                    color: #57606a;
                    border-left: 4px solid #d0d7de;
                }}
            </style>
        </head>

        <body>
            {rendered_markdown}
        </body>
    </html>
    """

    return HTMLResponse(content=html_document)
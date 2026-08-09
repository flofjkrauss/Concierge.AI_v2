from pathlib import Path

from api.routers.readme import prepare_mermaid_blocks, read_readme
from configuration.application import ApplicationSettings


def test_prepare_mermaid_blocks_preserves_diagram_content() -> None:
    rendered = '<pre><code class="language-mermaid">graph TD; A--&gt;B</code></pre>'

    assert prepare_mermaid_blocks(rendered) == (
        '<pre class="mermaid">graph TD; A--&gt;B</pre>'
    )


def test_prepare_mermaid_blocks_leaves_other_code_unchanged() -> None:
    rendered = '<pre><code class="language-python">print(1)</code></pre>'

    assert prepare_mermaid_blocks(rendered) == rendered


def test_read_readme_renders_markdown_and_mermaid(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Test App\n\n```mermaid\ngraph TD\nA-->B\n```\n",
        encoding="utf-8",
    )
    settings = ApplicationSettings(project_root=tmp_path, app_name="Test App")

    response = read_readme(settings)
    html = response.body.decode("utf-8")

    assert "<title>Test App</title>" in html
    assert "<h1>Test App</h1>" in html
    assert '<pre class="mermaid">' in html
    assert "mermaid.initialize" in html

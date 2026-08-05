"""Export validation results to HTML, JSON, or PDF."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Tuple

from jinja2 import Template
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.models.schemas import ExportFormat, ExportRequest, ValidationResponse

HTML_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Schema Validation Report</title>
  <style>
    body { font-family: Georgia, serif; margin: 2rem; background: #f7f5f2; color: #1a1a1a; }
    h1 { font-size: 1.6rem; }
    .pass { color: #0a7a35; }
    .fail { color: #b00020; }
    .card { background: #fff; border: 1px solid #ddd; padding: 1rem 1.25rem; margin: 1rem 0; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }
    th { background: #eee; }
    code { font-family: ui-monospace, monospace; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>API Schema Validation Report</h1>
  <p>Generated: {{ generated_at }}</p>
  <div class="card">
    <h2 class="{{ 'pass' if result.valid else 'fail' }}">
      {{ 'PASS' if result.valid else 'FAIL' }}
    </h2>
    <p>{{ result.message }}</p>
    <ul>
      <li>Total errors: {{ result.summary.total_errors }}</li>
      <li>Missing fields: {{ result.summary.missing_fields }}</li>
      <li>Invalid types: {{ result.summary.invalid_types }}</li>
      <li>Enum violations: {{ result.summary.enum_violations }}</li>
      <li>Additional properties: {{ result.summary.additional_properties }}</li>
      <li>Invalid formats: {{ result.summary.invalid_formats }}</li>
    </ul>
  </div>
  {% if result.errors %}
  <div class="card">
    <h3>Detailed Errors</h3>
    <table>
      <thead>
        <tr>
          <th>Category</th>
          <th>Message</th>
          <th>JSON Path</th>
          <th>Schema Path</th>
          <th>Line</th>
        </tr>
      </thead>
      <tbody>
        {% for e in result.errors %}
        <tr>
          <td>{{ e.category }}</td>
          <td>{{ e.message }}</td>
          <td><code>{{ e.json_path }}</code></td>
          <td><code>{{ e.schema_path }}</code></td>
          <td>{{ e.line_number or '' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}
</body>
</html>
"""
)


class ExportService:
    def export(self, request: ExportRequest) -> Tuple[bytes, str, str]:
        """
        Returns (content_bytes, media_type, filename).
        """
        if request.format == ExportFormat.JSON:
            payload = request.validation_result.model_dump(mode="json")
            data = json.dumps(payload, indent=2).encode("utf-8")
            return data, "application/json", "validation-report.json"

        if request.format == ExportFormat.HTML:
            html = HTML_TEMPLATE.render(
                result=request.validation_result,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            return html.encode("utf-8"), "text/html", "validation-report.html"

        if request.format == ExportFormat.PDF:
            return self._to_pdf(request.validation_result), "application/pdf", "validation-report.pdf"

        raise ValueError(f"Unsupported export format: {request.format}")

    def _to_pdf(self, result: ValidationResponse) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("API Schema Validation Report", styles["Title"]),
            Spacer(1, 12),
            Paragraph(
                f"<b>{'PASS' if result.valid else 'FAIL'}</b> — {result.message}",
                styles["Heading2"],
            ),
            Spacer(1, 8),
            Paragraph(
                f"Total errors: {result.summary.total_errors} | "
                f"Missing: {result.summary.missing_fields} | "
                f"Types: {result.summary.invalid_types} | "
                f"Enums: {result.summary.enum_violations}",
                styles["Normal"],
            ),
            Spacer(1, 16),
        ]

        if result.errors:
            rows = [["Category", "Message", "JSON Path", "Line"]]
            for e in result.errors[:50]:
                rows.append(
                    [
                        e.category.value,
                        (e.message[:80] + "…") if len(e.message) > 80 else e.message,
                        e.json_path,
                        str(e.line_number or ""),
                    ]
                )
            table = Table(rows, colWidths=[90, 250, 120, 40])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(table)

        doc.build(story)
        return buffer.getvalue()

from __future__ import annotations

from weasyprint import HTML, CSS


def render_booking_pdf_from_html(html: str, base_url: str) -> bytes:
    """
    Render HTML -> PDF using WeasyPrint.
    base_url must be an absolute URL or filesystem path so relative assets resolve.
    """
    # Extra compact overrides for A4 (does NOT affect your web template)
    compact_css = CSS(string="""
        @page { size: A4; margin: 10mm; }

        /* Ensure clean PDF */
        html, body { background: #fff !important; }
        .no-print { display: none !important; }

        /* Compact spacing */
        .ticket__header { padding: 14px 14px 10px !important; }
        .ticket__body { padding: 12px 14px 8px !important; }
        .ticket__footer { padding: 12px 14px !important; }
        .ticket__notes { padding: 10px 14px 12px !important; }

        .card { padding: 12px !important; box-shadow: none !important; }
        .ticket { box-shadow: none !important; }

        /* Keep two-column layout but compact */
        .grid { gap: 10px !important; }
        .meta { gap: 8px !important; }
        .meta__item { padding: 8px !important; }

        /* Table compact */
        thead th { padding: 10px 10px !important; font-size: 10px !important; }
        tbody td { padding: 10px 10px !important; font-size: 11px !important; }

        /* Prevent page break splitting a passenger row */
        tr { page-break-inside: avoid; }
        .card { page-break-inside: avoid; }
    """)

    pdf_bytes = HTML(string=html, base_url=base_url).write_pdf(stylesheets=[compact_css])
    return pdf_bytes
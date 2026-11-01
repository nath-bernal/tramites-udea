class CertificateRenderError(Exception):
    pass


def render_pdf(html: str, base_url: str | None = None) -> bytes:
    """Convierte HTML a PDF con WeasyPrint (importado aquí porque depende de librerías del SO)."""
    try:
        from weasyprint import HTML
    except OSError as exc:  # Pango/GLib no encontrados
        raise CertificateRenderError(
            "WeasyPrint no encontró sus librerías del sistema (Pango). En macOS: "
            "'brew install pango' y exporta DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib."
        ) from exc
    return HTML(string=html, base_url=base_url).write_pdf()

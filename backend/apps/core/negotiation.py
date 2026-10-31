"""Content negotiation helpers for binary download endpoints."""

from rest_framework.negotiation import DefaultContentNegotiation


class BinaryContentNegotiation(DefaultContentNegotiation):
    """Accept any ``Accept`` header on binary download actions.

    DRF negotiates before the handler runs. A browser asking for
    ``application/pdf`` would otherwise receive a 406 before the PDF response is
    constructed, because the viewset's renderers are JSON only. These actions
    return a Django ``HttpResponse`` directly, so the renderer is never used;
    selecting the first renderer simply lets the request through.
    """

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type

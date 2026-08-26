"""Logique de retry pour les erreurs transitoires (429, flux JP2 corrompus)."""

import time
from typing import Any

import pystac_client


# Snippets d'erreurs transitoires observées en pratique sur vsis3.
RETRYABLE_ERROR_SNIPPETS = (
    "429",
    "not recognized as being in a supported file format",
    "opj_get_decoded_tile",
    "stream too short",
    "failed to decode",
    "read failed",
    "segment too long",
)


def is_rate_limit_error(e: Exception) -> bool:
    """Détecte un 429 (rate limit) de façon robuste."""
    response = getattr(e, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    return "429" in str(e)


def is_retryable_error(e: Exception) -> bool:
    """
    Élargit is_rate_limit_error aux erreurs de flux JP2 corrompu sous charge
    (opj_get_decoded_tile, Stream too short, etc.).
    Ces erreurs sont transitoires : un retry récupère généralement un flux complet.
    """
    if is_rate_limit_error(e):
        return True
    msg = str(e).lower()
    return any(snippet in msg for snippet in RETRYABLE_ERROR_SNIPPETS)


def search_with_retry(
    catalog: pystac_client.Client,
    max_retries: int = 10,
    base_delay: int = 10,
    **search_kwargs: Any,
):
    """Recherche STAC avec retry sur 429."""
    for attempt in range(max_retries):
        try:
            search = catalog.search(**search_kwargs)
            return list(search.items())
        except Exception as e:
            if is_rate_limit_error(e):
                delay = base_delay * (2**attempt)
                print(
                    f"  Rate limit, attente {delay}s "
                    f"(tentative {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Échec de la recherche STAC après plusieurs tentatives")
import time


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
    """Détection un peu plus robuste que le seul string-matching sur '429'."""
    response = getattr(e, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    return "429" in str(e)


def is_retryable_error(e: Exception) -> bool:
    """
    Élargit is_rate_limit_error aux erreurs de flux JP2 corrompu sous charge
    (opj_get_decoded_tile, Stream too short, segment too long, format non
    reconnu) observées en pratique sur vsis3 avec plusieurs threads concurrents.
    Ces erreurs sont transitoires dans la grande majorité des cas : un retry
    récupère généralement un flux complet à l'essai suivant.
    """
    if is_rate_limit_error(e):
        return True
    msg = str(e).lower()
    return any(snippet in msg for snippet in RETRYABLE_ERROR_SNIPPETS)


def search_with_retry(catalog, max_retries=5, base_delay=10, **search_kwargs):
    for attempt in range(max_retries):
        try:
            search = catalog.search(**search_kwargs)
            return list(search.items())
        except Exception as e:
            if is_rate_limit_error(e):
                delay = base_delay * (2**attempt)
                print(f"Rate limit, attente {delay}s (tentative {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Échec après plusieurs tentatives")
"""Project-wide pytest configuration.

Default every test to *dry-run* external jobs so the suite never makes a real
HTTP call to the FastAPI/renderer services (which do not exist yet). Individual
tests override ``EXTERNAL_JOBS_ENABLED`` / ``EXTERNAL_JOBS_DRY_RUN`` via the
``settings`` fixture when they need the disabled or real-submission paths.
"""

import pytest


@pytest.fixture(autouse=True)
def _external_jobs_dry_run_by_default(settings):
    settings.EXTERNAL_JOBS_ENABLED = True
    settings.EXTERNAL_JOBS_DRY_RUN = True

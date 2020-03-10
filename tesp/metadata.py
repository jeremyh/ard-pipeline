from tesp.version import REPO_URL, __version__


def _get_eugl_metadata():
    return {
        "software_versions": {
            "tesp": {
                "version": __version__,
                "repo_url": REPO_URL,
            }
        }
    }

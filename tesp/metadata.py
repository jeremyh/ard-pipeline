from tesp.version import REPO_URL, get_version


def _get_tesp_metadata():
    return {
        "software_versions": {
            "tesp": {
                "version": get_version(),
                "repo_url": REPO_URL,
            }
        }
    }

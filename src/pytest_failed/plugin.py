import pytest


@pytest.hookimpl
def pytest_addoption(parser):
    group = parser.getgroup("failed", "helpers for failed test selections")
    group.addoption(
        "--dump-lf",
        metavar="FILENAME",
    )
    group.addoption(
        "--restore-lf",
        metavar="FILENAME",
    )


def load_nodeids(config, path):
    path = config.invocation_dir.join(path)
    if (prefix := config.rootdir.relto(config.invocation_dir)):
        prefix = f"{prefix}/"
    nodeids = {}
    known_garbage = frozenset(("ERROR", "FAILED"))
    for line in path.open("r"):
        parts = [x for x in line.strip().split() if x not in known_garbage]
        if parts:
            nodeid = parts[0]
            if nodeid.startswith(prefix):  # removeprefix with python 3.9
                nodeid = nodeid[len(prefix):]
            nodeids[nodeid] = True
    return nodeids


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if (path := config.option.restore_lf) and config.getoption("lf"):
        from _pytest.cacheprovider import Cache

        nodeids = load_nodeids(config, path)
        cache = Cache.for_config(config)
        cache.set("cache/lastfailed", nodeids)


@pytest.hookimpl(tryfirst=True)
def pytest_cmdline_main(config):
    if path := config.option.dump_lf:
        from _pytest.config import create_terminal_writer

        config._do_configure()
        tw = create_terminal_writer(config)
        lastfailed = config.cache.get("cache/lastfailed", {})
        nodeids = [f"{k}\n" for k, v in lastfailed.items() if v]
        path = config.invocation_dir.join(path)
        with path.open("w") as f:
            f.writelines(nodeids)
        tw.line("Wrote failed nodeids for:", bold=True)
        tw.line(str(config.rootdir))
        tw.line("to:", bold=True)
        tw.line(str(path))
        return 0
    if (path := config.option.restore_lf) and not config.getoption("lf"):
        from _pytest.config import create_terminal_writer

        config._do_configure()
        nodeids = load_nodeids(config, path)
        config.cache.set("cache/lastfailed", nodeids)
        if not config.getoption("lf"):
            tw = create_terminal_writer(config)
            tw.line(f"Restored {len(nodeids)} failed nodeids for:", bold=True)
            tw.line(str(config.rootdir))
            tw.line("from:", bold=True)
            tw.line(str(path))
            return 0
    return None

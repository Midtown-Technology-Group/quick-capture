from importlib.metadata import entry_points

def main() -> None:
    eps = entry_points(group="console_scripts")
    for ep in eps:
        if ep.name == "quick-capture":
            ep.load()()
            return
    raise SystemExit("Console script entry point not found: quick-capture")

if __name__ == "__main__":
    main()

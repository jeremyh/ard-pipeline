#!/usr/bin/env python3

from pathlib import Path

import yaml
from jinja2 import Template

BUILD_DIR = Path(__file__).parent


def main():
    pwd = BUILD_DIR
    (pwd / 'scripts').mkdir(exist_ok=True)

    with (pwd / 'module-config.yaml').open() as fl:
        variables = yaml.load(fl, Loader=yaml.SafeLoader)

    for path in (pwd / 'templates').iterdir():
        print('generating', path.name)
        with path.open() as fl:
            template = Template(fl.read())
        with (pwd / 'scripts' / path.name).open('w') as out:
            print(template.render(variables), file=out)


if __name__ == '__main__':
    main()

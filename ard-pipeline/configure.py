from pathlib import Path
from jinja2 import Template
import yaml

def main():
    pwd = Path.cwd()
    (pwd / 'scripts').mkdir(exist_ok=True)

    with open('module-config.yaml') as fl:
        variables = yaml.load(fl, Loader=yaml.SafeLoader)

    for path in (pwd / 'templates').iterdir():
        print('generating', path.name)
        with path.open() as fl:
            template = Template(fl.read())
        with (pwd / 'scripts' / path.name).open('w') as out:
            print(template.render(variables), file=out)

if __name__ == '__main__':
    main()

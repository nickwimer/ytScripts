import argparse
import os
import pkgutil
import subprocess


def list_scripts(directory):
    return [name for _, name, _ in pkgutil.iter_modules([directory])]


class ListScriptsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print("Available scripts:")
        for script in list_scripts(os.path.dirname(__file__)):
            script_path = os.path.join(os.path.dirname(__file__), f"{script}.py")
            print(f"\n{script} ({script_path})")
            try:
                subprocess.run(["python", script_path, "-h"], check=True)
            except subprocess.CalledProcessError:
                print(f"Failed to run --help on {script}")
        parser.exit()


def main():

    parser = argparse.ArgumentParser(
        description="ytScripts Data Extraction Packages",
        usage="%(prog)s script [script_args] [-h] [-l]",
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Name of the script to run within the data_extraction package",
    )
    parser.add_argument(
        "-l", "--list", nargs=0, help="List available scripts", action=ListScriptsAction
    )
    args, script_args = parser.parse_known_args()

    if args.script:
        print(f"Running {args.script} script with args: {script_args}")

        script_path = os.path.join(os.path.dirname(__file__), f"{args.script}.py")
        try:
            subprocess.run(["python", script_path] + script_args, check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to run {args.script} with args: {script_args}")

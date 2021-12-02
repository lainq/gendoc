import ast
import sys
import os
import re

from typing import Callable, List, Tuple, Dict


class ParserResult:
    summary = ""
    body = ""
    args = []
    returns = []
    arguments = []

    def __str__(self):
        value = f"({self.summary}){self.body}{self.args}"
        return value

    def __repr__(self):
        return self.__str__()


class DocstringParser:
    def __init__(self, source):
        self.source = source.split("\n") if source else []
        self.line_number = 0
        self.result = ParserResult()

    def get_blocks(self, break_condition: Callable) -> List[str]:
        value = []
        current_value = []
        while self.line_number < len(self.source):
            line = self.source[self.line_number]
            is_condition_true = break_condition(line.strip())
            if is_condition_true:
                value.append("\n".join(current_value))
                current_value = []
            current_value.append(line)
            self.line_number += 1
        return value

    def get_value(self, _list: List[str]) -> List[Tuple[str, str]]:
        arguments = []
        for value in _list:
            _value = value.strip()
            slices = _value.split(":")
            name, value = slices[0].split(" ")[0], ":".join(slices[1:])
            arguments.append((name, value))
        return arguments

    def parse(self) -> ParserResult:
        blocks = self.get_blocks(lambda line: len(line) == 0)
        for index, block in enumerate(blocks):
            if index == 0:
                self.result.summary = block
                continue
            lines = list(filter(lambda line: len(line) != 0, block.split("\n")))
            if len(lines) == 0:
                continue
            if lines[0] == "Args:":
                self.result.args = self.get_value(lines[1:])
                continue
            if lines[0] == "Returns:":
                self.result.returns = self.get_value(lines[1:])
                continue

            self.result.body = block
        return self.result


class FunctionArgument:
    """
    Argument for functions, with the name
    and the default value
    """

    def __init__(self, name, default_value):
        self.name = name
        self.default_value = default_value

    def __repr__(self):
        return f"<{self.name}:{self.default_value}>"


class Function(object):
    def __init__(self, node, parent=None):
        self.node = node

        self.parent = parent
        self.is_public = not (self.node.name.startswith("_"))

    def get_arguments(self) -> List[FunctionArgument]:
        args = self.node.args
        return_value, default_value_index = [], 0
        for argument in args.args:
            return_value.append(FunctionArgument(argument.arg, argument.annotation))
        if args.vararg:
            return_value.append(
                FunctionArgument("*" + args.vararg.arg, args.vararg.annotation)
            )
        if args.kwarg:
            return_value.append(
                FunctionArgument("**" + args.kwarg.arg, args.kwarg.annotation)
            )
        return return_value

    def get_docstrings(self):
        return ast.get_docstring(self.node)

    def __str__(self):
        parent = f"{'of ' + self.parent.name if self.parent else ''}"
        value = f"<{self.node.name}:{parent}>(public:{self.is_public})>"
        return value

    def __repr__(self):
        return self.__str__()


def generate_markdown(function: Function, result: ParserResult):
    markdown = f"**{function.node.name}**("
    for index, arg_name in enumerate(result.arguments):
        markdown += f"*{arg_name.name}*"
        if index != len(result.arguments) - 1:
            markdown += ", "
    markdown += ")"

    markdown += "\n"
    markdown += result.body + "\n" if result.body else result.summary + "\n"

    markdown += "\nParameters:\n" if len(result.args) > 0 else ""
    for arg in result.args:
        name, details = arg
        markdown += f"\n`{name}`: {details}\n"

    markdown += "\nReturn:\n" if len(result.returns) > 0 else ""
    for return_value in result.returns:
        type_, details = return_value
        markdown += f"\n`{type_}`: {details}\n"

    markdown += "\n<hr>\n\n"
    return markdown


def get_function_bodies(body, parent=None):
    functions = []
    for node in body:
        if isinstance(node, ast.FunctionDef):
            functions.append(Function(node, parent))
        elif isinstance(node, ast.ClassDef):
            functions.append(node)
            functions += get_function_bodies(node.body, node)
    return functions


def create_error(message, suggestion=None, fatal=True):
    print(f"[ERROR]: {message}")
    if suggestion:
        print(f"[TRY]: {suggestion}")
    if fatal:
        sys.exit()


def parse_arguments(arguments: List[str]) -> Tuple[str, Dict[str, str]]:
    command, parameters = "", {}
    for index, argument in enumerate(arguments):
        if index == 0:
            command = argument
            continue
        is_valid_argument = argument.startswith("--")
        if not is_valid_argument:
            create_error(f"[ERROR]: {argument} is not a valid argument")
        slices = argument.split("=")
        key, value = slices[0][2:], "=".join(slices[1:])
        if len(value) == 0:
            value = "True"
        parameters.setdefault(key, value)
    return command, parameters


def generate_docs(
    files: List[str],
    parameters: Dict[str, str],
    docs_dir=os.path.join(os.getcwd(), "docs"),
    init_only=None,
):
    if not os.path.isdir(docs_dir):
        os.mkdir(docs_dir)
    for filename in files:
        with open(filename, "r") as source_reader:
            content = source_reader.read()
            _ast = ast.parse(content)
            functions = get_function_bodies(_ast.body)

            output = ""
            for function in functions:
                if isinstance(function, ast.ClassDef):
                    if function.name.startswith("_"):
                        continue
                    docstrings = ast.get_docstring(function)
                    if not (docstrings and (len(function.body) > 0)):
                        continue
                    output += f"\n# `{function.name}`\n\n{docstrings}\n\n"
                    continue
                if not function.is_public:
                    continue
                parser = DocstringParser(function.get_docstrings())
                result = parser.parse()
                result.arguments = function.get_arguments()

                markdown = generate_markdown(function, result)
                output += markdown
            if init_only:
                docs_dir = os.path.join(
                    docs_dir, os.path.basename(os.path.dirname(filename))
                )
            os.makedirs(docs_dir, exist_ok=True)
            output_filename = os.path.join(
                docs_dir, os.path.basename(filename.split(".")[:-1][-1]) + ".md"
            )
            if os.path.exists(output_filename) and not (parameters.get("yes")):
                overrite_file = input(
                    f"Overrite {output_filename} [y/n] "
                ).strip().lower() in ["y", "yes"]
                if not overrite_file:
                    print(f"Skipping {filename}")
                    continue
            with open(output_filename, "w") as file_writer:
                file_writer.write(output)


class Gitignore:
    def __init__(self, dirname):
        self.patterns = self.get_gitignore_patterns(dirname)
        self.patterns.append(".git/")

    def get_gitignore_patterns(self, directory: str) -> List[str]:
        gitignore_file = os.path.join(directory, ".gitignore")
        print(gitignore_file)
        if not os.path.exists(gitignore_file):
            return []
        with open(gitignore_file, "r") as reader:
            return list(map(lambda line: line.strip(), reader.readlines()))

    def match(self, value):
        # TODO: match
        return value


def get_files(directory, recursive, init_only=None):
    content = list(
        filter(
            lambda file: os.path.isfile(file)
            and file.endswith(".py")
            and (file == "__init__.py" if init_only else True),
            os.listdir(directory),
        )
    )
    gitignore = Gitignore(directory)
    if not recursive:
        return content
    files = []
    for (root, _, filename) in os.walk(directory):
        for _file in filename:
            path = os.path.join(root, _file)
            if not _file.endswith(".py"):
                continue
            if init_only:
                if _file != "__init__.py":
                    continue
            path = os.path.join(root, _file)
            files.append(path)

    return files


def main():
    arguments = sys.argv[1:]
    command, parameters = parse_arguments(arguments)
    if command == "help":
        print(
            "gendoc <filename> --out=<output-folder(optional)> --init-only --recursive"
        )
    else:
        if not os.path.exists(command):
            create_error(f"{command}, file not found :/")
        output_dir = parameters.get("out") or os.path.join(
            command if os.path.isdir(command) else os.path.dirname(command), "docs"
        )
        if os.path.isfile(command):
            generate_docs([command], parameters, output_dir)
        elif os.path.isdir(command):
            init_only = parameters.get("init-only")
            files = get_files(command, parameters.get("recursive"), init_only)
            generate_docs(files, parameters, init_only=init_only)


if __name__ == "__main__":
    main()

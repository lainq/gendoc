import ast

from typing import Callable, List, Tuple

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

class DocstringParser():
  def __init__(self, source):
    self.source = source.split("\n") if source else []
    self.line_number = 0
    self.result = ParserResult()


  def get_blocks(self, break_condition:Callable) -> List[str]:
    value = []
    current_value = []
    while self.line_number < len(self.source):
      line = self.source[self.line_number]
      is_condition_true = break_condition(line.strip())
      if is_condition_true:
        value.append('\n'.join(current_value))
        current_value = []
      current_value.append(line)
      self.line_number += 1
    return value

  def get_value(self, _list:List[str]) -> List[Tuple[str, str]]:
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
  def __init__(self, name, default_value):
    self.name = name
    self.default_value = default_value

  def __repr__(self):
    return f"<{self.name}:{self.default_value}>"

class Function(object):
  def __init__(self, node, parent=None):
    self.node = node

    self.parent = parent
    self.is_public = not(self.node.name.startswith("_"))

  def get_arguments(self) -> List[FunctionArgument]:
    args = self.node.args
    return_value, default_value_index = [], 0
    for argument in args.args:
      return_value.append(FunctionArgument(argument.arg, argument.annotation))
    if args.vararg:
      return_value.append(FunctionArgument("*" + args.vararg.arg, args.vararg.annotation))
    if args.kwarg:
      return_value.append(FunctionArgument("**" + args.kwarg.arg, args.kwarg.annotation))
    return return_value

  def get_docstrings(self):
    return ast.get_docstring(self.node)

  def __str__(self):
    parent = f"{'of ' + self.parent.name if self.parent else ''}"
    value = f"<{self.node.name}:{parent}>(public:{self.is_public})>"
    return value

  def __repr__(self):
    return self.__str__()

def generate_markdown(function:Function, result:ParserResult):
  markdown = f"**{function.node.name}**("
  for index, arg_name in enumerate(result.arguments):
    markdown += f"*{arg_name.name}*"
    if index != len(result.arguments)-1:
      markdown += ", "
  markdown += "\n"
  markdown += result.body if result.body else result.summary

  markdown += ")"
  return markdown

def get_function_bodies(body, parent=None):
  functions = []
  for node in body:
    if isinstance(node, ast.FunctionDef):
      functions.append(Function(node, parent))
    elif isinstance(node, ast.ClassDef):
      functions += get_function_bodies(node.body, node)
  return functions

with open("test.py", "r") as reader:
  content = reader.read()
  _ast = ast.parse(content)

  functions = get_function_bodies(_ast.body)
  for function in functions:
    if not function.is_public:
      continue
    parser = DocstringParser(function.get_docstrings())
    result = parser.parse()
    result.arguments = function.get_arguments()

    markdown = generate_markdown(function, result)
    print(markdown)

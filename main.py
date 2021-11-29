import ast

class ParserResult:
  summary = None
  body = None
  args = []
  returns = []

class DocstringParser():
  def __init__(self, source):
    self.source = source.split("\n") if source else []
    self.line_number = 0
    self.result = ParserResult()

  def get_blocks(self, break_condition):
    value = []
    current_value = []
    while self.line_number < len(self.source):
      line = self.source[self.line_number]
      is_condition_true = break_condition(line.strip())
      if is_condition_true:
        value.append(current_value)
        current_value = []
      current_value.append(line)
      self.line_number += 1
    return value

  def parse(self):
    blocks = self.get_blocks(lambda line: len(line) == 0)
    for index, block in enumerate(blocks):
      pass    

class Function(object):
  def __init__(self, node, parent=None):
    self.node = node

    self.parent = parent
    self.is_public = not(self.node.name.startswith("_"))

  def get_docstrings(self):
    return ast.get_docstring(self.node)

  def __str__(self):
    parent = f"{'of ' + self.parent.name if self.parent else ''}"
    value = f"<{self.node.name}:{parent}>(public:{self.is_public})>"
    return value

  def __repr__(self):
    return self.__str__()

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
    parser = DocstringParser(function.get_docstrings())
    parser.parse()

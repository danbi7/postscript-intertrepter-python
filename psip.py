import logging
import math

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------------------------------
# SCOPING FLAG
# Set to True for lexical (static) scoping, False for dynamic scoping
# -------------------------------------------------------------------------------------
STATIC_SCOPING = False

# -------------------------------------------------------------------------------------
# PSDICT
# -------------------------------------------------------------------------------------
class PSDict:
    """PostScript Dictionary.
    
    In static scoping mode, the 'parent' pointer records which dictionary 
    was on top of the dict-stack at the moment 'dict' was called, 
    so that name look-up follows lexical chain rather than the runtime stack.
    """
    def __init__(self, capacity=0):
        self.dict = {}
        self.capacity = capacity    # 0 means unlimited (built-in dicts)
        self.parent = None          # Used in static-scoping mode

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __getitem__(self, key):
        return self.dict[key]
    
    def __contains__(self, item):
        return item in self.dict
    
    def set_parent(self, parent):
        self.parent = parent

    def length(self):
        return len(self.dict)
    
    def maxlength(self):
        return self.capacity if self.capacity else len(self.dict)
    
    def __repr__(self):
        return f"PSDICT({self.dict})"
    
    def __str__(self):
        return f"PSDICT({self.dict})"

class PSProcedure:
    """A procedure that remembers its definition-time dictionary (lexical closure)."""
    def __init__(self, tokens, defining_dict):
        self.tokens = tokens                # list of token strings
        self.defining_dict = defining_dict  # PSDict on top of dict_stack at def-time

    def __repr__(self):
        return f"PSProcedure({self.tokens})"
    

# -------------------------------------------------------------------------------------
# EXCEPTIONS
# -------------------------------------------------------------------------------------
class ParseFailed(Exception):
    """ An exception indicating that a parser failed to parse the input """
    def __init__(self, message):
        super().__init__(message)

class TypeMismatch(Exception):
    """ An exception indicating that a type mismatch happend in function/operation invocation """
    def __init__(self, message):
        super().__init__(message)


# -------------------------------------------------------------------------------------
# PARSERS
# -------------------------------------------------------------------------------------
def process_boolean(input):
    logging.debug(f"Input to process_boolean: {input}")
    if input == "true":
        return True
    elif input == "false":
        return False
    else:
        raise ParseFailed("Can't parse input into boolean")
    
def process_number(input):
    try:
        float_value = float(input)
        if float_value.is_integer():
            return int(float_value)
        else:
            return float_value
    except ValueError:
        raise ParseFailed("Can't parse input into a number")
    
def process_name_constant(input):
    if input.startswith("/"):
        return input
    else:
        raise ParseFailed("Can't parse input into a name constant")
    
def process_code_block(input):
    if len(input) >= 2 and input.startswith("{") and input.endswith("}"):
        inner = input[1:-1].strip()
        if inner == "":
            return []
        return tokenize(inner)
    else:
        raise ParseFailed("Can't parse input into a name")
    
def process_string_literal(input):
    if input.startswith("(") and input.endswith(")"):
        return input[1:-1]
    else:
        raise ParseFailed("Can't parse input into a string literal")
    

PARSERS = [
    process_boolean,
    process_number,
    process_name_constant,
    process_code_block,
    process_string_literal
]


def process_constants(input):
    for parser in PARSERS:
        try:
            return parser(input)
        except ParseFailed:
            continue
    raise ParseFailed(f"Could not parse {input}")


# -------------------------------------------------------------------------------------
# TOKENIZER
# -------------------------------------------------------------------------------------
def tokenize(text):
    """Split PostScript source into tokens.
    
    Handles:
        1. Nested { } code blocks returned as a single token
        2. ( ) string literals returned as a single token
        3. Ordinary withespace-delimited tokens
    """
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        # Skip whitespace
        if text[i].isspace():
            i += 1
            continue
        
        # Nested code block
        if text[i] == '{':
            depth = 0
            j = i
            while j < n:
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        tokens.append(text[i:j + 1])
                        i = j + 1
                        break
                j += 1
            else:
                tokens.append(text[i:]) # Unclosed
                break
            continue

        # String literal
        if text[i] == '(':
            j = i + 1
            while j < n and text[j] != ')':
                j += 1
            tokens.append(text[i:j + 1])
            i = j + 1
            continue

        # Ordinary token
        j = i
        while j < n and not text[j].isspace():
            j += 1
        tokens.append(text[i:j])
        i = j

    return tokens


# -------------------------------------------------------------------------------------
# GLOBAL STACKS
# -------------------------------------------------------------------------------------
op_stack = []
dict_stack = []
dict_stack.append(PSDict()) # Built-in dictionary


# -------------------------------------------------------------------------------------
# HELPER: Look up a name, respecting current scoping mode
# -------------------------------------------------------------------------------------
def _lookup(name):
    if STATIC_SCOPING:
        return _lookup_static(name)
    else:
        return _lookup_dynamic(name)
    
def _lookup_static(name):
    current = dict_stack[-1]
    while current is not None:
        if name in current:
            return current[name], True
        current = current.parent
    return None, False

def _lookup_dynamic(name):
    for d in reversed(dict_stack):
        if name in d:
            return d[name], True
    return None, False


# -------------------------------------------------------------------------------------
# BUILT-IN OPERATIONS
# -------------------------------------------------------------------------------------
# 1) Stack operations
def exch_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("exch requires 2 operands")
    a = op_stack.pop()
    b = op_stack.pop()
    op_stack.append(a)
    op_stack.append(b)

def pop_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("pop requires 1 operand")
    op_stack.pop()

def copy_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("copy requires at least 1 operand")
    n = op_stack.pop()
    if not isinstance(n, int) or n < 0:
        raise TypeMismatch("copy requires a non-negative integer")
    if len(op_stack) < n:
        raise TypeMismatch("copy: not enough elements on stack")
    top_n = op_stack[-n:]   # Slice (does not remove!)
    op_stack.extend(top_n)

def dup_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("dup requires 1 operand")
    op_stack.append(op_stack[-1])

def clear_operation():
    op_stack.clear()

def count_operation():
    op_stack.append(len(op_stack))


# 2) Arithmetic operations
def add_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("add requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    op_stack.append(a + b)

def sub_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("sub requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    op_stack.append(a - b)
    
def mul_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("mul requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    op_stack.append(a * b)

def div_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("mul requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    if b == 0:
        raise TypeMismatch("div: division by zero")
    op_stack.append(a / b)

def idiv_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("idiv requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    if b == 0:
        raise TypeMismatch("idiv: division by zero")
    op_stack.append(int(a / b)) # Truncate toward zero

def mod_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("mod requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    if b == 0:
        raise TypeMismatch("mod: division by zero")
    op_stack.append(a % b)

def abs_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("abs requires 1 operand")
    op_stack.append(abs(op_stack.pop()))

def neg_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("neg requires 1 oeprand")
    op_stack.append(-op_stack.pop())

def ceiling_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("ceiling requires 1 oeprand")
    v = op_stack.pop()
    result = math.ceil(v)
    op_stack.append(float(result) if isinstance(v, float) else result)

def floor_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("floor requires 1 oeprand")
    v = op_stack.pop()
    result = math.floor(v)
    op_stack.append(float(result) if isinstance(v, float) else result)

def round_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("round requires 1 oeprand")
    v = op_stack.pop()
    result = math.floor(v + 0.5)
    op_stack.append(float(result) if isinstance(v, float) else result)

def sqrt_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("sqrt requires 1 oeprand")
    v = op_stack.pop()
    if v < 0:
        raise TypeMismatch("sqrt: negative number")
    op_stack.append(math.sqrt(v))


# 3) Dictionary operations
def dict_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("dict requires 1 oeprand")
    capacity = op_stack.pop()
    if not isinstance(capacity, int):
        raise TypeMismatch("dict: capacity must be an integer")
    new_dict = PSDict(capacity=capacity)
    if STATIC_SCOPING:
        new_dict.set_parent(dict_stack[-1])
    op_stack.append(new_dict)

def length_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("length requires 1 operand")
    obj = op_stack.pop()
    if isinstance(obj, PSDict):
        op_stack.append(obj.length())
    elif isinstance(obj, (str, list)):
        op_stack.append(len(obj))
    else:
        raise TypeMismatch(f"lengthL unsupported type {type(obj)}")

def maxlength_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("maxlength requires 1 operand")
    obj = op_stack.pop()
    if isinstance(obj, PSDict):
        op_stack.append(obj.maxlength())
    else:
        raise TypeMismatch("maxlength: operand must be a dictionary")

def begin_operation():
    if len(dict_stack) < 1:
        raise TypeMismatch("begin: stack is empty")
    d = op_stack.pop()
    if not isinstance(d, PSDict):
        raise TypeMismatch("begin: top of stack is not a dictionary")
    if STATIC_SCOPING and d.parent is None and len(dict_stack) > 0:
        d.set_parent(dict_stack[-1])
    dict_stack.append(d)

def end_operation():
    if len(dict_stack) <= 1:
        raise TypeMismatch("end: cannot pop the built-in dictionary")
    dict_stack.pop()

def def_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("def requires 2 operands")
    value = op_stack.pop()
    key = op_stack.pop()
    if isinstance(key, str) and key.startswith("/"):
        key = key[1:]
        if STATIC_SCOPING and isinstance(value, list):
            value = PSProcedure(value, dict_stack[-1])
        dict_stack[-1][key] = value
    else:
        op_stack.append(key)
        op_stack.append(value)
        raise TypeMismatch("def: key must be a name constant (/name)")
    

# 4) String operations
def get_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("get requires 2 operands")
    index = op_stack.pop()
    obj = op_stack.pop()
    if isinstance(obj, str) and isinstance(index, int):
        if index < 0 or index >= len(obj):
            raise TypeMismatch("get: index out of range")
        op_stack.append(ord(obj[index]))
    else:
        raise TypeMismatch("get: requires string and integer")
    
def getinterval_operation():
    if len(op_stack) < 3:
        raise TypeMismatch("getinterval requires 3 operands")
    count = op_stack.pop()
    index = op_stack.pop()
    obj = op_stack.pop()
    if isinstance(obj, str) and isinstance(index, int) and isinstance(count, int):
        if index < 0 or count < 0 or index + count > len(obj):
            raise TypeMismatch("getinterval: index/count out of range")
        op_stack.append(obj[index:index + count])
    else:
        raise TypeMismatch("getinterval: requires string, int, int")

def putinterval_operation():
    if len(op_stack) < 3:
        raise TypeMismatch("putinterval requires 3 operands")
    replacement = op_stack.pop()
    index = op_stack.pop()
    target = op_stack.pop()
    if isinstance(target, str) and isinstance(index, int) and isinstance(replacement, str):
        if index < 0 or index + len(replacement) > len(target):
            raise TypeMismatch("putinterval: index out of range")
        result = target[:index] + replacement + target[index + len(replacement):]
        op_stack.append(result)
    else:
        raise TypeMismatch("putinterval: requires string, int, string")


# 5) Boolean / Relational operations
def _compare(op_name):
    if len(op_stack) < 2:
        raise TypeMismatch(f"{op_name} requires 2 oeprands")
    b = op_stack.pop()
    a = op_stack.pop()
    if type(a) != type(b):
        raise TypeMismatch(f"{op_name}: operands must be the same type")
    return a, b

def eq_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("eq requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    op_stack.append(a == b)

def ne_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("ne requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    op_stack.append(a != b)

def ge_operation():
    a, b = _compare("ge")
    op_stack.append(a >= b)

def gt_operation():
    a, b = _compare("gt")
    op_stack.append(a > b)

def le_operation():
    a, b = _compare("le")
    op_stack.append(a <= b)

def lt_operation():
    a, b = _compare("lt")
    op_stack.append(a < b)

def and_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("and requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    if isinstance(a, bool) and isinstance(b, bool):
        op_stack.append(a and b)
    elif isinstance(a, int) and isinstance(b, int):
        op_stack.append(a & b)
    else:
        raise TypeMismatch("and: both operands must be bool or both int")

def or_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("or requires 2 operands")
    b = op_stack.pop()
    a = op_stack.pop()
    if isinstance(a, bool) and isinstance(b, bool):
        op_stack.append(a or b)
    elif isinstance(a, int) and isinstance(b, int):
        op_stack.append(a | b)
    else:
        raise TypeMismatch("or: both operands must be bool or both int")

def not_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("not requires 1 operands")
    v = op_stack.pop()
    if isinstance(v, bool):
        op_stack.append(not v)
    elif isinstance(v, int):
        op_stack.append(~v)
    else:
        raise TypeMismatch("not: operand must be bool or int")
    
def true_operation():
    op_stack.append(True)

def false_operation():
    op_stack.append(False)


# 6) Flow control operations
def execute_procedure(proc):
    for token in proc:
        process_input(token)

def if_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("if requires 2 operands")
    proc = op_stack.pop()
    cond = op_stack.pop()
    if not isinstance(cond, bool):
        raise TypeMismatch("if: condition must be a boolean")
    if not isinstance(proc, list):
        raise TypeMismatch("if: procedure must be a code block")
    if cond:
        execute_procedure(proc)

def ifelse_operation():
    if len(op_stack) < 3:
        raise TypeMismatch("ifelse requires 3 operands")
    proc2 = op_stack.pop()
    proc1 = op_stack.pop()
    cond = op_stack.pop()
    if not isinstance(cond, bool):
        raise TypeMismatch("ifelse: condition must be a boolean")
    if not isinstance(proc1, list) or not isinstance(proc2, list):
        raise TypeMismatch("ifelse: procedures must be a code blocks")
    if cond:
        execute_procedure(proc1)
    else:
        execute_procedure(proc2)

def for_operation():
    if len(op_stack) < 4:
        raise TypeMismatch("for requires 4 oeprands")
    proc = op_stack.pop()
    limit = op_stack.pop()
    step = op_stack.pop()
    initial = op_stack.pop()
    if not isinstance(proc, list):
        raise TypeMismatch("for: procedure must be a code block")
    i = initial
    while (step > 0 and i <= limit) or (step < 0 and i >= limit):
        op_stack.append(i)
        execute_procedure(proc)
        i += step
        # Keep numeric type consistetnt
        if isinstance(initial, int) and isinstance(step, int) and isinstance(limit, int):
            i = int(i)

def repeat_operation():
    if len(op_stack) < 2:
        raise TypeMismatch("repeat requires 2 operands")
    proc = op_stack.pop()
    n = op_stack.pop()
    if not isinstance(n, int) or n < 0:
        raise TypeMismatch("repeat: count must be a non-negative integer")
    if not isinstance(proc, list):
        raise TypeMismatch("repeat: procedure must be a code block")
    for _ in range(n):
        execute_procedure(proc)


# 7) I/O operations
def print_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("print requires 1 operand")
    v = op_stack.pop()
    if not isinstance(v, str):
        raise TypeMismatch("print: operand must be a string")
    print(v, end="")

def pop_print_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("= requires 1 operand")
    v = op_stack.pop()
    print(_ps_repr_simple(v))

def pop_print_ps_operation():
    if len(op_stack) < 1:
        raise TypeMismatch("== requires 1 operand")
    v = op_stack.pop()
    print(_ps_repr_full(v))

def _ps_repr_simple(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        return "{" + " ".join(v) + "}"
    if isinstance(v, PSDict):
        return "-dict-"
    return str(v)

def _ps_repr_full(v):
    if isinstance(v, str):
        return f"({v})"
    return _ps_repr_simple(v)


# -------------------------------------------------------------------------------------
# REGISTER ALL BUILT_INS
# -------------------------------------------------------------------------------------
_builtins = {
    # Stack
    "exch": exch_operation,
    "pop": pop_operation,
    "copy": copy_operation,
    "dup": dup_operation,
    "clear": clear_operation,
    "count": count_operation,
    # Arithmetic
    "add": add_operation,
    "sub": sub_operation,
    "mul": mul_operation,
    "div": div_operation,
    "idiv": idiv_operation,
    "mod": mod_operation,
    "abs": abs_operation,
    "neg": neg_operation,
    "ceiling": ceiling_operation,
    "floor": floor_operation,
    "round": round_operation,
    "sqrt": sqrt_operation,
    # Dictionary
    "dict": dict_operation,
    "length": length_operation,
    "maxlength": maxlength_operation,
    "begin": begin_operation,
    "end": end_operation,
    "def": def_operation,
    # String
    "get": get_operation,
    "getinterval": getinterval_operation,
    "putinterval": putinterval_operation,
    # Boolean / Relational
    "eq": eq_operation,
    "ne": ne_operation,
    "ge": ge_operation,
    "gt": gt_operation,
    "le": le_operation,
    "lt": lt_operation,
    "and": and_operation,
    "or": or_operation,
    "not": not_operation,
    "true": true_operation,
    "false": false_operation,
    # Flow control
    "if": if_operation,
    "ifelse": ifelse_operation,
    "for": for_operation,
    "repeat": repeat_operation,
    # I / O
    "print": print_operation,
    "=": pop_print_operation,
    "==": pop_print_ps_operation,
}

for name, fn in _builtins.items():
    dict_stack[0][name] = fn


# -------------------------------------------------------------------------------------
# LOOKUP (Dynamic vs Static)
# -------------------------------------------------------------------------------------
def lookup_in_dictionary(name):
    for d in reversed(dict_stack):
        if name in d:
            value = d[name]
            _dispatch(value)
            return
    raise ParseFailed(f"Could not find '{name}' in any dictionary")

def lookup_in_dictionary_static(name):
    current = dict_stack[-1]
    while current is not None:
        if name in current:
            value = current[name]
            _dispatch(value)
            return
        current = current.parent
    raise ParseFailed(f"Could not find '{name}' in lexical scope chain")

def _dispatch(value):
    if callable(value):
        value()
    elif isinstance(value, PSProcedure):
        # Push the definition-time dict so lookup follows the lexical chain
        dict_stack.append(value.defining_dict)
        try:
            execute_procedure(value.tokens)
        finally:
            dict_stack.pop()
    elif isinstance(value, list):
        execute_procedure(value)
    else:
        op_stack.append(value)


# -------------------------------------------------------------------------------------
# MAIN PROCESS-INPUT ENTRY POINT
# -------------------------------------------------------------------------------------
def process_input(token):
    try:
        res = process_constants(token)
        op_stack.append(res)
    except ParseFailed:
        try:
            if STATIC_SCOPING:
                lookup_in_dictionary_static(token)
            else:
                lookup_in_dictionary(token)
        except ParseFailed as e:
            logging.warning(str(e))


# -------------------------------------------------------------------------------------
# REPL
# -------------------------------------------------------------------------------------
def repl():
    """Read-Eval-Print Loop.

    Collects multi-token lines
    Handles { } blocks that span tokens
    """
    buffer = ""
    brace_depth = 0
    paren_depth = 0

    print("PostScript Interpreter (type 'quit to exit)")
    print(f"Scoping mode: {'Static (lexical)' if STATIC_SCOPING else 'DYNAMIC'}")

    while True:
        prompt = "REPL> " if not buffer else " ... "
        try:
            line = input(prompt)
        except EOFError:
            break

        for c in line:
            if c == '{':
                brace_depth += 1
            elif c == '}':
                brace_depth -= 1
            elif c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1

        if buffer:
            buffer += " " + line
        else:
            buffer = line

        # Only process when all braces/parens are balanced
        if brace_depth > 0 or paren_depth > 0:
            continue

        brace_depth = 0
        paren_depth = 0
        line_to_process = buffer.strip()
        buffer = ""

        if not line_to_process:
            continue
            
        tokens = tokenize(line_to_process)
        for token in tokens:
            if token.lower() == "quit":
                print("Goodbye.")
                return
            process_input(token)
        
        logging.debug(f"Operand Stack: {op_stack}")


if __name__ == "__main__":
    repl()
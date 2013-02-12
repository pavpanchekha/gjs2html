#!/usr/bin/env python
# https://gist.github.com/pavpanchekha/4746965

import re
import sys
import functools

class Debug:
    def __init__(self):
        self.tags = set()

    def __call__(self, *args, end="\n", sep=" ", tag=None):
        if not tag or tag in self.tags:
            print("[{}]".format(tag or "!"), *args,
                  end=end, sep=sep, file=sys.stderr)

    def __getattr__(self, attr):
        return functools.partial(self, tag=attr)

debug = Debug()

class Block(list):
    def __init__(self, tag, body="", **kwargs):
        list.__init__(self)
        self.tag = tag
        self.body = body
        self.attrs = kwargs

    def push(self, val):
        self.append(val)
        val.parent = self

    def has_parent(self, tag):
        block = self
        while not isinstance(block, Document):
            if block.tag == tag:
                return block
            else:
                block = self.parent
        return False

    def __bool__(self):
        return True

    def to_html(self):
        tag, body, attr = self.tag, self.body, self.attrs
        if tag == "pre":
            attr["data-lang"] = "scheme"
            body = body.strip() # Remove extra newlines from the end
        elif tag == "note":
            tag = "aside"
            attr["class"] = "note"
        elif tag == "pset":
            tag = "section"
            attr["class"] = "pset"

        if "_class" in attr:
            attr["class"] = attr["_class"]
            del attr["_class"]

        return tag, body, attr

class Document(Block):
    def __init__(self):
        Block.__init__(self, object())
        self.closed = True
        self.body = None
        self.title = "6.945 Problem Set"
        self.parent = None

def count_prefix(line, char):
    for i, lchar in enumerate(line):
        if lchar != char:
            return i
    return len(line)

class Parser:
    precedence = ["heading", "code", "pset", "pset_heading", "note", "ws", "text"]

    def __init__(self, nextline):
        self.nextline = nextline
        self.doc = Document()
        self.block = self.doc

    def parseline(self):
        line = self.nextline()

        if not line:
            return False

        debug.input(line, end="")
        for linetype in self.precedence:
            rec_fn = getattr(self, "rec_" + linetype)
            do_fn = getattr(self, "do_" + linetype)
            if rec_fn(line, self.doc, self.block):
                debug.rec(linetype, "::", self.block.tag,
                          hasattr(self.block, "closed"), end="")
                self.block = do_fn(line, self.doc, self.block)
                debug.rec("->", self.block.tag, hasattr(self.block, "closed"))
                if not (isinstance(self.block, Block) or
                        isinstance(self.block, Document)): raise TypeError("do_" + linetype + " returned " + repr(self.block))
                return True
        raise Exception("No valid line type found")

    def parse(self):
        header = ""
        for i in range(8):
            header += self.nextline()

        self.do_header(header)

        while self.parseline(): pass
        return self.doc

    def do_header(self, head):
        lines = head.split("\n")[:-1]
        if not (lines[0].isspace() or not lines[0]):
            lines.insert(0, "")
            lines.pop()
        l1, l2, l3, l4, l5, l6, l7, l8 = lines

        assert not l1 or l1.isspace(), "First line is not empty"
        assert "MASSACHVSETTS INSTITVTE OF TECHNOLOGY" in l2, "No MIT header line"
        assert "Department of Electrical Engineering and Computer Science" in l3, \
            "No EECS header line"

        header = Block("header")
        header.push(Block("h1", "MASSACHVSETTS INSTITVTE OF TECHNOLOGY"))
        header.push(Block("h2", "Department of Electrical Engineering and Computer Science"))

        assert not l4 or l4.isspace(), "Fourth line is not empty"

        assert l5.strip().startswith("6.94"), "Not for a '6.94x' series class"
        header.push(Block("h3", l5.strip(), _class="when"))
        assert l6.strip().startswith("Problem Set"), "Not for a problem set"
        header.push(Block("h3", l6.strip(), _class="pset"))
        self.doc.title = l6.strip()
        assert not l7 or l7.isspace(), "Seventh line is not empty"

        l8parts = map(str.strip, l8.strip().split(" "*8))
        issued, due = (part.strip() for part in l8parts if not part.isspace() and part)
        assert issued.startswith("Issued:"), "No issued date"
        assert due.startswith("Due:"), "No due date"
        issued = issued[len("Issued:"):].strip()
        due = due[len("Due:"):].strip()
        header.push(Block("time", issued, _class="issued"))
        header.push(Block("time", due, _class="due"))
        header.push(Block("hr"))
        header.closed = True

        self.doc.push(header)
        self.block = header

    def rec_heading(self, line, document, block):
        return any(i.isupper() for i in line) \
            and all(i.isalnum() or i.isspace() for i in line) \
            and not "(" in line \
            and (line.startswith("\t"*2) or line.startswith(" " * 10))

    def do_heading(self, line, document, block):
        head = Block("h1", line.strip())
        document.push(head)
        return head

    def rec_code(self, line, document, block):
        if block.tag == "note" and not hasattr(block, "closed"):
            return False

        if block.tag == "pre":
            return line.startswith(" " * 4) or line.startswith("\t") or line.isspace()
        else:
            return line.startswith(" " * 4) and hasattr(block, "closed")

    def do_code(self, line, document, block):
        if block.tag == "pre":
            line = line.replace("\t", " " * 8)
            if line.isspace():
                block.body += "\n"
            else:
                block.body += line[block.indent:]
            return block
        else:
            indent = count_prefix(line, " ")
            code = Block("pre", line[indent:])
            code.indent = indent
            block.parent.push(code)
            return code

    def rec_note(self, line, document, block):
        return line.startswith("*Note:")

    def do_note(self, line, document, block):
        note = Block("note", line[len("*Note:"):])
        if hasattr(block, "closed"):
            block.parent.push(note)
        else:
            block.push(note)
        return note

    def rec_pset(self, line, document, block):
        dashcount = line.count("-")
        return dashcount == len(line.strip()) and dashcount > 5

    def do_pset(self, line, document, block):
        pset = block.has_parent("pset")
        debug.rec("[{}]".format("starting" if pset is False else "ending"))

        if pset is False: # Starting a new pset block
            pset = Block("pset")
            document.push(pset)
            return pset
        else: # Ending an existing pset
            pset.closed = True
            return pset

    def rec_pset_heading(self, line, document, block):
        pset = block.has_parent("pset")
        if pset and not hasattr(pset, "title"):
            return line.startswith("Problem ")
        else:
            return False

    def do_pset_heading(self, line, document, block):
        pset = block.has_parent("pset")
        pset.title = line.strip()
        title = Block("h1", line.strip())
        pset.push(title)
        return title

    def rec_ws(self, line, document, block):
        return line.isspace()

    def do_ws(self, line, document, block):
        pset = block.has_parent("pset")

        if pset is not False and not hasattr(pset, "closed"):
            if len(pset):
                block = pset[-1]
                block.closed = True

            return block
        else:
            block.closed = True
            return block

    def rec_text(self, line, document, block):
        return True

    def do_text(self, line, document, block):
        if hasattr(block, "closed") or block.tag == "pre":
            p = Block("p", line)
            block.parent.push(p)
            return p
        else:
            block.body += line
            return block

def to_html(document, fd):
    print("<!doctype html>")
    print("<html lang='en_US'>")
    print("<head><title>{}</title>".format(document.title))
    print("<link rel='stylesheet' href='gjs.css' />")
    print("</head>")
    print("<body>")
    print("")

    for child in document:
        to_html_block(child, fd)

    print("")
    print("</body>")
    print("</html>")

def not_really_escape(s):
    # Prof. Sussman isn't expected to be malicious
    return s.replace("&", "&amp;").replace("<", "&lt;") \
        .replace(">", "&gt;").replace("\"", "&quot;")

def to_html_block(block, fd):
    tag, body, attrs = block.to_html()
    debug.out(tag, attrs)
    open_tag = "<{}".format(tag)
    for attr, value in attrs.items():
        open_tag += " "
        open_tag += attr
        if value == True:
            pass
        else:
            open_tag += "=\""
            open_tag += not_really_escape(value)
            open_tag += "\""
    open_tag += ">"
    print(open_tag, end="")
    print(not_really_escape(body), end="")

    for child in block:
        to_html_block(child, fd)

    print("</{}>".format(tag))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", help="Turn on debugging",
                        default=[],
                        type=functools.partial(str.split, sep=","))
    args = parser.parse_args()
    debug.tags.update(args.debug)

    parser = Parser(sys.stdin.readline)
    to_html(parser.parse(), sys.stdout)

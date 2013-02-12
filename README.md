<!-- -*- type: markdown -*- -->

gjs2html - Convert Prof. Sussman's Problem Sets to HTML
=======================================================

Professor Sussman hands out problem sets in plain text.  Why?  Plain
text lasts forever, and you don't need any special software to read
it.  Plain text is universal.

It is not, however, typographically sophisticated.  `gjs2html` parses
plain text marked up as Prof. Sussman tends to mark up text, and
produces a semi-beautiful HTML version of the text.

Requirements and Installation
-----------------------------

`gjs2html` requires a Python 3 installation.  No non-standard
libraries are used.  To install, just copy the script somewhere.

Running gjs2html
----------------

`gjs2html` is run from the command line, like so:

    python3 gjs2html.py < ps.txt > ps.html

Currently only Unix pipes are supported for input and output.

The output HTML file should be placed in the same directory as a
`gjs.css` file; one is supplied with the project.

`gjs2html` is capable of producing copious debug output, reflecting
internal parser state as it goes through the document.  This is
enabled with the `-d` option, which takes a list of debug tags to
output:

    python3 gjs2html.py -d input,rec,out < ps.txt > ps.html

Debug output is printed to standard error.  The debug tags are:

 + `input`: Prints each line of input as it is read
 + `rec`: Prints some information about the recognition process run
   for each line and the current document tree state.
 + `out`: Prints some information about each HTML tag that is output.
 
Implementation
--------------

`gjs2html` read the file one line at a time, in a single pass.  First,
a document tree is built, and then in a second pass the document tree
is output to HTML.  Each line of input is fed through a sequence of
recognizers; if any of them recognize the line, recognition terminates
and a handler associated with the recognizer is run on the line.

The document tree mirrors the eventual HTML structure, though usually
with more descriptive tag names.  Each recognizer, and each associated
handler, is passed the a reference to the top of the document tree and
a reference to the bottom-right-most (most recent) node, as well of
course as the current line of text.  Some recognizers inspect the
document tree; for example, a line of whitespace may break between
paragraphs, but not if the current node of the document tree is a
block of code, since whitespace lines are preserved there.

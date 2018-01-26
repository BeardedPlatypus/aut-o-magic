# Elm scripts

## tasks.py

`tasks.py` provides pyinvoke command line functions to automate compilation. 
Because many of my projects are organised in a similar fashion, this allows me
to have a simpler set of function to compile my project with.

### Usage

The script currently provides the following function:

    invoke compile --elm --html --css --verbose
    
Where the flags control which parts should be compiled. Without flags it 
compiles everything.

### Dependencies

`tasks.py` makes use of [pyinvoke](http://www.pyinvoke.org)


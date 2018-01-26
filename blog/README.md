# Blog scripts

## tasks.py

`tasks.py` provides pyinvoke command line functions to automate pelican blog 
maintenance. 

### Usage

The script currently provides the following functions:

    invoke update_content
    
to copy new content placed in the `content` folder to either the preview or
production folder.

    invoke compile_preview --run
    
to compile a preview of the current blog. Run specifies whether it should 
run the preview on `localhost 8000` through blender.

    invoke preview_current

Run the current preview on `localhost 8000`

    invoke compile_publish
    
to compile the production version of the current blog.


### Dependencies

`tasks.py` makes use of [pyinvoke](http://www.pyinvoke.org)

# Vim Color Term
Python script to create pseudo-terminal having color scheme derived from a vim color scheme

This script scans a vim color scheme file or files in a directory and converts a random one to Xresources
arguments to feed to a new xterm or rxvt-unicode terminal in order to get a terminal colored
as the chosen vim color scheme.

It requires either xterm or rxvt-unicode (urxvt) to be installed, as well as vim and,
ideally, a good rich set of vim color schemes (try [here](https://github.com/flazz/vim-colorschemes)).

Typical use is to replace the typical command set for opening a terminal.
For example, in `.config/openbox/rc.xml`:
```xml
     ...
     <!-- my shortcuts -->
     <keybind key="C-A-T">
       <action name="Execute">
         <command>~/.vim_color_term.py --urxvt ~/.vim/colors/*</command>
       </action>
     </keybind>
     ...
```

## Usage:

To create a terminal (xterm is default) from a standard vim colorscheme package (Vim 8.1, in this case):
```bash
$ python3 vim_color_term.py /usr/share/vim/vim81/colors/*.vim
```
To create a terminal from one's local color schemes:
```bash
$ python3 vim_color_term.py ~/.vim/colors/*.vim
```
To create a terminal from color schemes set by the `GOOD_ONES` variable:
```bash
$ python3 vim_color_term.py
```
To create an urxvt terminal from one's local color schemes:
```bash
$ python3 vim_color_term.py --urxvt ~/.vim/colors/*.vim
```
For help:
```bash
$ python3 vim_color_term.py --help
```
## Screenshot
![Screenshot showing results of repeated calls of the script](http://vapid.io/images/vim_color_term_screenshot.png)

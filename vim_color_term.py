#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

'''
Scan a vim color scheme file or files in a directory and convert a random one to Xresources
arguments to feed to a new xterm or rxvt-unicode terminal in order to get a terminal colored
as the chosen vim color scheme.

It requires either xterm or rxvt-unicode (urxvt) to be installed, as well as vim and,
ideally, a good rich set of vim color schemes (try: https://github.com/flazz/vim-colorschemes).

Typical use is to replace the typical command set for opening a terminal.
For example, in .config/openbox/rc.xml:
     ...
     <!-- my shortcuts -->
     <keybind key="C-A-T">
       <action name="Execute">
         <command>~/.vim_color_term.py --urxvt ~/.vim/colors/*</command>
       </action>
     </keybind>
     ...

'''
import re
import os
import sys
import glob
import math
import random
import argparse
import subprocess
from pathlib import Path

### ----------------------------- Adjust-as-needed constants --------------------------------- ###
# Adjust this accordingly or install the terminus fonts via Debian/Ubuntu 'xfonts-terminus' package
FONT_NAME = 'Anonymous Pro Regular'
BOLD_FONT_NAME = 'Anonymous Pro Bold'
ITALIC_FONT_NAME = 'Anonymous Pro Italic'
BOLD_ITALIC_FONT_NAME = 'Anonymous Pro Bold Italic'
FONT_SIZE = 11

# Set this to the system vim runtime value ($VIMRUNTIME in vim)
# It will be (crudely) guessed if this isn't set
VIMRUNTIME = ''

# In the created Terminal, this variable will hold the name of the file used to generate the colors
# Examine to figure out which color scheme was chosen so it may be added to the GOOD_ONES list below
ENV_COLOR_SCHEME_NAME_VAR = "VIM_COLOR_TERM_COLOR_SCHEME_FILE"

# xterm command (via -xrm argument) XResources will be primed with this stuff (customize these)
XTERM_XRESOURCES = [
    'xterm*termName: xterm-256color',
    'xterm*loginShell: true',
    'xterm*dynamicColors: true',
    'xterm.vt100.blink: true',
    'XTerm.vt100.locale : true',
    'XTerm.vt100.scrollBar: true',
    'XTerm.vt100.scrollbar.width: 8',
    'xterm*faceName: {0}'.format(FONT_NAME),
    'xterm*faceSize: {0}'.format(FONT_SIZE),
    'xterm*saveLines: 200000',
    'xterm*visualBell: True',
    'xterm*boldMode: true',
    'xterm*renderFont: true'
]

# urxvt command (via -xrm argument) XResources will be primed with this stuff (customize these)
URXVT_XRESOURCES = [
    'URxvt.termName: rxvt-unicode-256color',
    'URxvt.font: xft:{0}:style=Regular:size={1}'.format(FONT_NAME, FONT_SIZE),
    'URxvt.boldFont: xft:{0}:style=Bold:size={1}'.format(FONT_NAME, FONT_SIZE),
    'URxvt.italicFont: xft:{0}:style=Italic:size={1}'.format(FONT_NAME, FONT_SIZE),
    'URxvt.boldItalicfont: xft:{0}:style=Bold Italic:size={1}'.format(FONT_NAME, FONT_SIZE),
    'URxvt.letterSpace: 0',
    'URxvt.lineSpace: 0',
    'URxvt.geometry: 80x24',
    'URxvt.internalBorder: 0',
    'URxvt.cursorBlink: true',
    'URxvt.cursorUnderline: false',
    'URxvt.saveLines: 200000',
    'URxvt.scrollBar: true',
    'URxvt.scrollBar_right: false',
    'URxvt.urgentOnBell: true',
    'URxvt.depth: 24',
    'URxvt.iso14755: false',
]

# kitty command (via -o argument) config vaules will be primed with this stuff (customize these or use a config file)
KITTY_OPTIONS = [
    'term=xterm-kitty',
    'font_size={0}'.format(FONT_SIZE),
    'font_family={0}'.format(FONT_NAME),
    'bold_font={0}'.format(BOLD_FONT_NAME),
    'italic_font={0}'.format(ITALIC_FONT_NAME),
    'bold_italic_font={0}'.format(BOLD_ITALIC_FONT_NAME),
    'scrollback_lines=200000',
    'kitty_mod=super',
]

# If no vim color scheme files are provided via the command-line, prefer these (customize these)
GOOD_ONES = [
    'rastafari', 'hilal', 'smyck', 'iceberg',\
    'selenitic', 'pacific', 'mushroom', 'vimbrant',\
    'graywh', 'darkslategray', 'tir_black'
]

# Vim color schemes directory in which to search for GOOD_ONES
GOOD_ONES_VIM_COLORS_DIR = '{0}/.vim/colors'.format(Path.home())

# This maps the particular color scheme elements to ANSI and extended xterm color codes
# Adjust as needed to make mappings more sensible; this mostly works
MAPPINGS = {
    'foreground': r'.*Normal.*?guifg=([#\w]+).*',
    'background': r'.*Normal.*?guibg=([#\w]+).*',

    'color0': r'.*Comment.*?guifg=([#\w]+).*',      # <ESC>[30m (black)
    'color1': r'.*ErrorMsg.*?guifg=([#\w]+).*',     # <ESC>[31m (red)
    'color2': r'.*Type.*?guifg=([#\w]+).*',         # <ESC>[32m (green)
    'color3': r'.*WarningMsg.*?guifg=([#\w]+).*',   # <ESC>[33m (yellow)
    'color4': r'.*PreProc.*?guifg=([#\w]+).*',      # <ESC>[34m (blue)
    'color5': r'.*Special.*?guifg=([#\w]+).*',      # <ESC>[35m (magenta)
    'color6': r'.*Search.*?guifg=([#\w]+).*',       # <ESC>[36m (cyan)
    'color7': r'.*Todo.*?guifg=([#\w]+).*',         # <ESC>[37m (white)

    'color8': r'.*Comment.*?guifg=([#\w]+).*',      # black
    'color9': r'.*ErrorMsg.*?guifg=([#\w]+).*',     # red
    'color10': r'.*Type.*?guifg=([#\w]+).*',        # green
    'color11': r'.*WarningMsg.*?guifg=([#\w]+).*',  # yellow
    'color12': r'.*PreProc.*?guifg=([#\w]+).*',     # blue
    'color13': r'.*Special.*?guifg=([#\w]+).*',     # magenta
    'color14': r'.*Search.*?guifg=([#\w]+).*',      # cyan
    'color15': r'.*Todo.*?guifg=([#\w]+).*'         # white
}

# Color scheme to show if all else fails; think a tasty cherry milkshake
FAILSAFE_COLOR_SCHEME = {
    "background": "#fbe7eb",
    "foreground": "#130a0d",
    "color0":  "#000000",
    "color1":  "#d80f14",
    "color2":  "#777777",
    "color3":  "#671012",
    "color4":  "#26266b",
    "color5":  "#f09fac",
    "color6":  "#46464b",
    "color7":  "#ffffff",
    "color8":  "#000000",
    "color9":  "#d80f14",
    "color10": "#77777b",
    "color11": "#8e1417",
    "color12": "#6a4751",
    "color13": "#fbe7eb",
    "color14": "#9a5d6e",
    "color15": "#ffffff"
}

### ---------------------------- END adjust-as-needed constants -------------------------------- ###

URXVT_COMMAND = 'urxvt'
URXVT_XRESOURCES_PREFIX = '-xrm'
KITTY_COMMAND = 'kitty'
KITTY_OPTIONS_PREFIX = '-o'
XTERM_COMMAND = 'xterm'
XTERM_XRESOURCES_PREFIX = '-xrm'

# If not set, try to guess the VIMRUNTIME
if not VIMRUNTIME:
    VIMRUNTIME_GLOB = glob.glob('/usr/share/vim/vim[78][0-9]')
    if VIMRUNTIME_GLOB:
        VIMRUNTIME = VIMRUNTIME_GLOB[0]
    else:
        sys.exit(\
            'ERROR: failed to find vim runtime; (set VIMRUNTIME to proper value or install vim)')

NAMED_COLORS = {}

def load_vim_named_colors():
    """
    Load the mappings of vim colors to hex strings
    """
    try:
        color_regex = re.compile(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(.*)$')
        with open(VIMRUNTIME + '/rgb.txt', 'r') as rgbfile:
            for line in rgbfile:
                color_matcher = color_regex.match(line)
                if color_matcher is not None and color_matcher.groups(1) is not None:
                    NAMED_COLORS[color_matcher.groups()[3].lower()] = \
                        "{0:02x}{0:02x}{0:02x}".format(\
                        *(int(color) for color in color_matcher.groups()[0:3]))

    # pylint: disable=broad-except
    except Exception as ex:
        sys.exit("ERROR: failed to load vim rgb.txt: {0}".format(ex))


def color_distance(color_a_hex_string, color_b_hex_string):
    """
    Find some distance between two colors as an attempt to determine contrast
    """
    color_a_tuple = (int(color_a_hex_string[:2], 16), int(color_a_hex_string[2:4], 16),\
        int(color_a_hex_string[4:6], 16))
    color_b_tuple = (int(color_b_hex_string[:2], 16), int(color_b_hex_string[2:4], 16),\
        int(color_b_hex_string[4:6], 16))

    rmean = (color_a_tuple[0] + color_b_tuple[0]) / 2
    red = color_a_tuple[0] - color_b_tuple[0]
    green = color_a_tuple[1] - color_b_tuple[1]
    blue = color_a_tuple[2] - color_b_tuple[2]
    return math.sqrt(((int(512+rmean) * red * red) >> 8) + 4 * green * green +\
        ((int(767 - rmean) * blue * blue) >> 8))

# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
def generate_options(filename, options, option_format):
    """
    Generate a list of options arguments expected by the terminals from a vim color scheme file
    """
    resource_hex_values = {}
    compiled_mappings =\
        {option: re.compile(this_regex) for (option, this_regex) in MAPPINGS.items()}
    hex_regex = re.compile('#([0-9a-f]{6})')

    for option, reggie in compiled_mappings.items():
        with open(filename, 'r') as vimfile:
            for line in vimfile:
                matcher = reggie.match(line)
                if matcher is not None and matcher.groups(1) is not None:
                    vim_color_value = matcher.groups()[0].lower()
                    if vim_color_value in NAMED_COLORS.keys():
                        hex_value = NAMED_COLORS[vim_color_value]
                    elif vim_color_value in ('fg', 'bg'):
                        # set as "fg" or "bg" values for now, we'll
                        # resolve these below once we're certain we have
                        # valid values for foreground and background
                        hex_value = vim_color_value
                    else:
                        hex_matcher = hex_regex.match(vim_color_value)
                        if hex_matcher is not None and hex_matcher.groups(1) is not None:
                            hex_value = hex_matcher.groups()[0]
                        else:
                            raise Exception('invalid hex: ' + vim_color_value)

                    resource_hex_values[option] = hex_value
                    break

    # Adjust colors too close to background and set them to the foreground
    background_color = resource_hex_values['background']
    foreground_color = resource_hex_values['foreground']
    if background_color is None or foreground_color is None:
        raise Exception('no background or foreground color')

    for resource, color in resource_hex_values.items():
        if color == 'fg':
            resource_hex_values[resource] = foreground_color
        elif color == 'bg':
            resource_hex_values[resource] = background_color
        elif resource != 'background':
            # This attempts to prevent a light foreground on a light background or a dark foreground
            # on a dark background but it doesn't work really well
            distance = color_distance(color, background_color)
            if distance < 10.0:
                resource_hex_values[resource] = foreground_color

    if not resource_hex_values:
        raise Exception('invalid format')

    return options + sorted([option_format.format(resource, hex_value)\
        for resource, hex_value in resource_hex_values.items()])


# pylint: disable=invalid-name
if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(\
        description='convert vim color file to Xresources/xtermcontrol config')
    PARSER.add_argument('vim_files', nargs='*', help='a set of vim color scheme files to process')

    GROUP = PARSER.add_mutually_exclusive_group()
    GROUP.add_argument('--xterm', action='store_true', help='create an xterm terminal')
    GROUP.add_argument('--urxvt', action='store_true', help='create an urxvt terminal')
    GROUP.add_argument('--kitty', action='store_true', help='create an kitty terminal')

    PARSED_ARGS = PARSER.parse_args()

    VIM_FILES = PARSED_ARGS.vim_files if PARSED_ARGS.vim_files else\
        ['{0}/{1}.vim'.format(GOOD_ONES_VIM_COLORS_DIR, vim_file) for vim_file in GOOD_ONES]

    GLOBBED_FILES = [item for sublist in [glob.glob(given_filename)\
        for given_filename in VIM_FILES] for item in sublist]

    random.shuffle(GLOBBED_FILES)

    load_vim_named_colors()

    command = []
    term_environment = os.environ.copy()

    for vim_file in GLOBBED_FILES:
        try:
            if PARSED_ARGS.urxvt:
                raw_options = [[URXVT_XRESOURCES_PREFIX, option] for option in generate_options(vim_file, URXVT_XRESOURCES, 'URxvt*{0}: #{1}')]
                command = [URXVT_COMMAND] + [option for squashed in raw_options for option in squashed]
            elif PARSED_ARGS.kitty:
                raw_options = [[KITTY_OPTIONS_PREFIX, option] for option in generate_options(vim_file, KITTY_OPTIONS, "{0}=#{1}")]
                command = [KITTY_COMMAND] + [option for squashed in raw_options for option in squashed]
            else:
                raw_options = [[XTERM_XRESOURCES_PREFIX, option] for option in generate_options(vim_file, XTERM_XRESOURCES, "xterm*{0}: #{1}")]
                command = [XTERM_COMMAND] + [option for squashed in raw_options for option in squashed]

            term_environment[ENV_COLOR_SCHEME_NAME_VAR] = vim_file

            break
        # pylint: disable=bare-except
        except:
            # Ignore crap file and try another
            pass

    print("command: ", command)

    with subprocess.Popen(command, stdout=subprocess.PIPE, env=term_environment) as process:
        (stdout, stderr) = process.communicate()
        return_code = process.wait()

        if return_code:
            if stderr is None:
                error = ""
            else:
                error = stderr.decode()
                sys.exit("ERROR: '{0}' command error: {1} {2}".format(\
                    command, stdout.decode(), error))
        print(stdout.decode())

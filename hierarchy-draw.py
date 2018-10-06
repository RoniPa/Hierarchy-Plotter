import os
import sys
import click
import re

import networkx as nx
import matplotlib.pyplot as plt


def parse(txt, start_p, end_p):
    count = 0
    i = 0
    res = ''

    while True:
        c = txt[i]
        if (c == start_p):
            count += 1
        elif(c == end_p):
            count -= 1

        if (count == 0):
            break

        i += 1
        res += c
    return res[1:]


def parse_properties(props, txt):
    types = []
    for p in props:
        ind = txt.find('${};'.format(p))
        if ind != -1:
            cls_ind = txt.rfind('@var', 0, ind)
            t = txt[cls_ind+1:].split(' ', 2)[1]
            if t.find('<') > -1:
                t = t[t.find('<')+1:t.find('>')]
            types.append(t.split('|', 1)[0].strip())
    return types


def map_to_types(txt, assocs, prop_to):
    assoc_types = parse_properties(assocs, txt)
    prop_types = parse_properties(prop_to, txt)
    return (assoc_types, prop_types)


def parse_ac(txt):
    start_p = '@AccessControl'
    open_p = '('
    close_p = ')'

    class_name = ''
    assoc_arr = []
    prop_arr = []

    i = txt.find(start_p)
    if i > -1:
        s_i = i+len(start_p)
        e_i = len(txt)-1
        result = parse(txt[s_i:e_i], open_p, close_p)
        class_name = re.split(
            r'( |\{)',
            txt[txt.find('class ')+6:], 1)[0].strip()

        a_i = result.find('byAssociation=')
        if a_i > -1:
            assoc = parse(result[(a_i+14):], '{', '}')
            assoc_arr = [
                s.strip()
                for s in assoc.replace('"', '')
                .replace('*', '').split(',')
            ]

        p_i = result.find('propagateTo=')
        if p_i > -1:
            prop = parse(result[(p_i+12):], '{', '}')
            prop_arr = [
                s.strip()
                for s in prop.replace('"', '')
                .replace('*', '').split(',')
            ]

    return (class_name, assoc_arr, prop_arr)


def draw(rmap, outpath):
    G = nx.DiGraph()
    G.add_nodes_from(rmap.keys())
    print(rmap)

    for k, val in rmap.items():
        G.add_edges_from([(a, k) for a in val[0]])
        G.add_edges_from([(k, p) for p in val[1]])

    nx.draw_circular(G, with_labels=True, font_weight='light')
    plt.savefig(outpath)


def call_click_command(cmd, *args, **kwargs):
    """ Wrapper to call a click command

    :param cmd: click cli command function to call
    :param args: arguments to pass to the function
    :param kwargs: keywrod arguments to pass to the function
    :return: None 
    """

    # Get positional arguments from args
    arg_values = {c.name: a for a, c in zip(args, cmd.params)}
    args_needed = {c.name: c for c in cmd.params
                   if c.name not in arg_values}

    # build and check opts list from kwargs
    opts = {a.name: a for a in cmd.params if isinstance(a, click.Option)}
    for name in kwargs:
        if name in opts:
            arg_values[name] = kwargs[name]
        else:
            if name in args_needed:
                arg_values[name] = kwargs[name]
                del args_needed[name]
            else:
                raise click.BadParameter(
                    "Unknown keyword argument '{}'".format(name))

    # check positional arguments list
    for arg in (a for a in cmd.params if isinstance(a, click.Argument)):
        if arg.name not in arg_values:
            raise click.BadParameter("Missing required positional"
                                     "parameter '{}'".format(arg.name))

    # build parameter lists
    opts_list = sum(
        [[o.opts[0], str(arg_values[n])] for n, o in opts.items()], [])
    args_list = [str(v) for n, v in arg_values.items() if n not in opts]

    # call the command
    cmd(opts_list + args_list)


@click.command()
@click.option('-p', '--path', help='Source path (e.g. "./src/")')
@click.option('-o', '--output', help='Output file (e.g. "./chart.jpg")')
@click.option('-e', '--encoding', default='utf8',
              help='File encoding. Defaults to UTF-8.',
              type=click.Choice(['utf8', 'latin-1', 'ascii']))
def recurse_files(path, output, encoding):

    if (path is None):
        path = click.prompt('Give source root: (e.g. "./src/")', type=str)

    if (output is None):
        output = click.prompt('Give output file: (e.g. "./chart.jpg")',
                              type=str)

    result_map = {}

    for root, directories, filenames in os.walk(path):
        files = (x for x in filenames if x.endswith('.php'))
        for filename in files:
            txt = ''
            try:
                with (open(
                    os.path.join(root, filename),
                    encoding=encoding)
                ) as f:
                    txt = f.read()

                name, assocs, prop_to = parse_ac(txt)
                if name != '':
                    result_map[name] = map_to_types(txt, assocs, prop_to)

            except:
                click.echo(
                    click.style(
                        'Unexpected error: {}'.format(sys.exc_info()[0]),
                        fg="red"))

                raise click.Abort()

    draw(result_map, output)

    click.echo("File generated at %s" % output)
    click.echo("Have a nice day! :)")


if __name__ == "__main__":
    call_click_command(recurse_files,
                       'path/to/sources',
                       './lol-output', 'utf8')

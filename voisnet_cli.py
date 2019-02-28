"""
    Team VoIS-Network
    Purpose: VoIS-Network CLI
    Author: Shikha Suneja
"""

import click
from network_visualization import *
import matplotlib.pyplot as plt

TOPOLOGY_IMAGE = 'static/topology.png'

@click.command()
@click.option("--intent", prompt="Enter an intent",
              help="The intent to be passed to the VoISNet application")
def voisnet_cli(intent):
    """ Simple program that takes an intent from the user and takes action
        accordingly
    """

    click.echo("The user intent is - \"%s\"!" % intent)
    if "visualize topology" or "show topology" in intent:
        visualize_topology(cli = True)
        plt.show()


if __name__ == '__main__':
    voisnet_cli()

from __future__ import annotations
import numpy as np
# pylint: disable=unused-import
from challenge import (
    TYPE_PIERRE,
    TYPE_CISEAUX,
    TYPE_FEUILLE,
    BasePlayer
)
import random


class Player(BasePlayer):
    DIRECTIONS=((0, 1), (0, -1), (1, 0), (-1, 0))
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Utiliser self.config pour acceder à la configuration de la partie si nécéssaire (lecture seule)
        self.name = 'Partiellement Aléatoire'
        self.dir = 0

    # pylint: disable=unused-argument
    def play(
        self,
        maze: np.array,
        myPosition: tuple[int, int],
        enemyPosition: tuple[int, int],
        myType: int,
        enemyType: int,
        myScore: int,
        enemyScore: int,
    ):
        d = self.DIRECTIONS[self.dir]
        p = (myPosition[0] + d[0], myPosition[1] + d[1])
        if maze[p[1]][p[0]] == -1:
            self.dir = random.randrange(len(self.DIRECTIONS))
            d = self.DIRECTIONS[self.dir]
            p = (myPosition[0] + d[0], myPosition[1] + d[1])
            while maze[p[1]][p[0]] == -1:
                self.dir = (self.dir + 1) % len(self.DIRECTIONS)
                d = self.DIRECTIONS[self.dir]
                p = (myPosition[0] + d[0], myPosition[1] + d[1])
        return p

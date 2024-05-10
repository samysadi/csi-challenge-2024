# Vous ne devez RIEN modifier dans ce fichier
# On vous demandera de modifier uniquement le fichier player1.py (ou player2.py)
# Vous pouvez utiliser le code dans main.py pour simuler une partie

# #################################################################################################

"""
Copyright 2024 Sadi Samy <samy.sadi at ummto.dz>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import annotations
import copy
import inspect
import os
import random
import pygame
import numpy as np
import signal
import time
import traceback

TYPE_PIERRE = 0
TYPE_CISEAUX = 1
TYPE_FEUILLE = 2

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Timed out")

class ChallengeConfig:
    def __init__(
        self, width: int,
        height: int,
        steps: int,
        stepDelay: int = 50,
        delayToRun: int = 3,
        randomSeed: int = None,
        wallColor: pygame.color.ColorValue = (0, 0, 0),
        floorColor: pygame.color.ColorValue = (255, 255, 255),
        bgColor: pygame.color.ColorValue = (0, 0, 0),
        title: str = 'Challenge CSI',
        player1Color: pygame.color.ColorValue = (0,0,255),
        player2Color: pygame.color.ColorValue = (255,0,0),
        scoreColor: pygame.color.ColorValue = (255, 255, 255),
        miscColor: pygame.color.ColorValue = (255, 255, 255),
        windowWidth: int = 1200,
        windowHeight: int = 700,
        marginLeft: int = 280,
        marginRight: int = 10,
        marginTop: int = 10,
        marginBottom: int = 10,
        score1Value: int = 3,
        score2Value: int = 11,
        scoreMinValue: int = -10,
        scoreNegativeValue: int = -4,
        scoreCrossValue: int = 17,
        scoreOnException: int = -50,
        scoreOnBadMove: int = -20,
        scoreOnTimeout: int = -15,
        countScore1: float = 0.25,
        countScore2: float = 0.10,
        countScoreMin: float = 0.15,
        countRefresh: float = 0.05,
        maxTime: int = 500,
        enableRPCGame: bool = True,
        regenerateCells: bool = False,
        playSounds: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.steps = steps
        self.stepDelay = stepDelay
        self.delayToRun = delayToRun
        self.randomSeed = randomSeed
        self.wallColor = wallColor
        self.floorColor = floorColor
        self.bgColor = bgColor
        self.windowWidth = windowWidth
        self.windowHeight = windowHeight

        self.marginLeft = marginLeft
        self.marginRight = marginRight
        self.marginTop = marginTop
        self.marginBottom = marginBottom

        self.score1Value = score1Value
        self.score2Value = score2Value
        self.scoreMinValue = scoreMinValue
        self.scoreNegativeValue = scoreNegativeValue
        self.scoreCrossValue = scoreCrossValue
        self.scoreOnException = scoreOnException
        self.scoreOnBadMove = scoreOnBadMove
        self.scoreOnTimeout = scoreOnTimeout

        self.countScore1 = countScore1
        self.countScore2 = countScore2
        self.countScoreMin = countScoreMin
        self.countRefresh = countRefresh

        self.title = title
        self.scoreColor = scoreColor
        self.miscColor = miscColor

        self.maxTime = maxTime

        self.enableRPCGame = enableRPCGame
        self.regenerateCells = regenerateCells
        self.playSounds = playSounds

        self.player1Color = player1Color
        self.player2Color = player2Color

class Challenge(ChallengeConfig):
    TYPES = [TYPE_PIERRE, TYPE_CISEAUX, TYPE_FEUILLE]
    TYPE_LABELS = ['Pierre', 'Ciseaux', 'Feuille']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.currentStep = 0
        self.runTime = None
        self.runTimeElapsed = False

        self.running = False
        self.surface = None

        self.useAlarmSignal = os.name != 'nt'

        pygame.init()
        pygame.display.set_caption(self.title)
        self.createSurface()
        self.createIcons()
        self.createSounds()

        font = pygame.font.Font(None, 32)
        self.star1Text = font.render("Entre 1 et " + str(self.score1Value) + " points", True, self.miscColor)
        self.star2Text = font.render("Entre " + str(self.score1Value + 1) + " et " + str(self.score2Value) + " points", True, self.miscColor)
        self.star3Text = font.render("Entre -3 et " + str(self.scoreMinValue) + " points", True, self.miscColor)
        self.refreshText = font.render("Changement de type", True, self.miscColor)

        font = pygame.font.Font(None, 32)
        self.typeTexts = []
        for t in self.TYPE_LABELS:
            t = font.render(t, True, self.miscColor)
            self.typeTexts.append(t)

        self.scoreFont = pygame.font.Font(None, 42)

        self.player1 = None
        self.player2 = None

        self.player1Score = 0
        self.player2Score = 0

        self.random = random.Random(self.randomSeed) 
        self.maze = self.genMaze(self.width, self.height, self.random)
        self.width, self.height = len(self.maze[0]), len(self.maze)

        self.player1Position = (0, 0)
        self.player2Position = (0, 0)

        self.player1Position = self.genPlayerPosition()
        self.player2Position = self.genPlayerPosition()

        self.player1Type = self.random.choice(self.TYPES)
        self.player2Type = self.random.choice(self.TYPES)

        self.player1Text = None
        self.player2Text = None

        self.generateMazeCellsForScore1(int(self.countScore1 * self.emptyCellsCount))
        self.generateMazeCellsForScore2(int(self.countScore2 * self.emptyCellsCount))
        self.generateMazeCellsForScoreMin(int(self.countScoreMin * self.emptyCellsCount))
        if self.enableRPCGame:
            self.generateMazeCellsForRefresh(int(self.countRefresh * self.emptyCellsCount))

    @property
    def emptyCellsCount(self):
        return np.count_nonzero(self.maze == 0)

    @property
    def cellHeight(self):
        sh = self.windowHeight - self.marginTop - self.marginBottom
        return sh // self.height

    @property
    def cellWidth(self):
        sw = self.windowWidth - self.marginLeft - self.marginRight
        return sw // self.width

    def cloneConfig(self):
        constructorSignature = inspect.signature(ChallengeConfig.__init__)
        kwargs = {}
        for param in constructorSignature.parameters.values():
            if param.name == 'self':
                continue
            kwargs[param.name] = copy.deepcopy(getattr(self, param.name))
        return ChallengeConfig(**kwargs)

    @staticmethod
    def compareTypes(t1, t2):
        if t1 == t2:
            return 0
        if t1 == TYPE_PIERRE:
            if t2 == TYPE_CISEAUX:
                return 1
            else:
                return -1
        elif t1 == TYPE_CISEAUX:
            if t2 == TYPE_PIERRE:
                return -1
            else:
                return 1
        else:
            if t2 == TYPE_PIERRE:
                return 1
            else:
                return -1

    def createIcons(self):
        IconsPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
        self.Star1Image = pygame.image.load(os.path.join(IconsPath, '1.png')).convert_alpha()
        self.Star2Image = pygame.image.load(os.path.join(IconsPath, '2.png')).convert_alpha()
        self.Star3Image = pygame.image.load(os.path.join(IconsPath, '3.png')).convert_alpha()
        self.RefreshImage = pygame.image.load(os.path.join(IconsPath, 'refresh.png')).convert_alpha()
        self.P1Image = pygame.image.load(os.path.join(IconsPath, 'p1.png')).convert_alpha()
        self.P2Image = pygame.image.load(os.path.join(IconsPath, 'p2.png')).convert_alpha()

    def createSurface(self):
        self.surface = pygame.display.set_mode((self.windowWidth, self.windowHeight), pygame.RESIZABLE)

    def createSounds(self):
        SoundsPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')
        if self.playSounds:
            self.Star1Sound = pygame.mixer.Sound(os.path.join(SoundsPath, 'Score1.ogg'))
            self.Star2Sound = pygame.mixer.Sound(os.path.join(SoundsPath, 'Score2.ogg'))
            self.Star3Sound = pygame.mixer.Sound(os.path.join(SoundsPath, 'Score3.ogg'))
            self.RefreshSound = pygame.mixer.Sound(os.path.join(SoundsPath, 'Refresh.ogg'))
            self.CrossSound = pygame.mixer.Sound(os.path.join(SoundsPath, 'Cross.ogg'))
        else:
            emptySound = None
            self.Star1Sound = emptySound
            self.Star2Sound = emptySound
            self.Star3Sound = emptySound
            self.RefreshSound = emptySound
            self.CrossSound = emptySound

    def drawMargin(self):
        x0, y0 = 10, 50
        mx0, mx1, mx2 = 40, 10, 64
        my1, my2, my3, my4, my5 = 10, 100, 100, 100, 35

        maxTextWidth = self.marginLeft - self.P1Image.get_width() - mx0

        self.surface.blit(self.P1Image, (x0, y0 + (self.player1Text.get_height() - self.P1Image.get_height()) // 2))
        t = self.drawText(self.player1Text, pygame.Rect(x0 + mx1 + self.P1Image.get_width(), y0, min(maxTextWidth, self.player1Text.get_width()), self.player1Text.get_height()))

        y0 += t.get_height() + my1
        t = self.typeTexts[self.player1Type]
        self.drawText(t, pygame.Rect(x0 + mx2 + mx1, y0, t.get_width(), t.get_height()))

        y0 += t.get_height() + my1
        st = str(int(self.player1Score))
        st = self.scoreFont.render(st, True, self.scoreColor)
        self.drawText(st, pygame.Rect(x0 + mx1 + self.P1Image.get_width(), y0, min(maxTextWidth, st.get_width()), st.get_height()))

        if self.player2:
            y0 += my2
            self.surface.blit(self.P2Image, (x0, y0 + (self.player2Text.get_height() - self.P2Image.get_height()) // 2))
            t = self.drawText(self.player2Text, pygame.Rect(x0 + mx1 + self.P2Image.get_width(), y0, min(maxTextWidth, self.player2Text.get_width()), self.player2Text.get_height()))

            y0 += t.get_height() + my1
            t = self.typeTexts[self.player2Type]
            self.drawText(t, pygame.Rect(x0 + mx2 + mx1, y0, t.get_width(), t.get_height()))

            y0 += t.get_height() + my1
            st = str(int(self.player2Score))
            st = self.scoreFont.render(st, True, self.scoreColor)
            self.drawText(st, pygame.Rect(x0 + mx1 + self.P2Image.get_width(), y0, min(maxTextWidth, st.get_width()), st.get_height()))

        y0 += my3
        st = 'Étape: ' + str(int(self.currentStep)) + " / " + str(int(self.steps)) 
        st = self.scoreFont.render(st, True, self.scoreColor)
        self.drawText(st, pygame.Rect(x0 + mx1, y0, min(maxTextWidth, st.get_width()), st.get_height()))

        y0 += my4
        for i, t in ((self.Star1Image, self.star1Text),(self.Star2Image, self.star2Text),(self.Star3Image, self.star3Text),(self.RefreshImage, self.refreshText) if self.enableRPCGame else (None, None),):
            if not i:
                continue
            i = pygame.transform.scale(i, (32, 32))
            self.surface.blit(i, (x0, y0 + (t.get_height() - i.get_height()) // 2))
            self.drawText(t, pygame.Rect(x0 + mx1 + i.get_width(), y0, x0 + mx1 + min(maxTextWidth, t.get_width()), y0 + t.get_height()))
            y0 += my5

    def drawText(self, t: pygame.Surface, rect: pygame.Rect):
        tr = t.get_rect()
        r = min(rect.width / tr.width, rect.height / tr.height)
        rect.width = int(tr.width * r)
        rect.height = int(tr.height * r)
        t = pygame.transform.scale(t, rect.size)
        self.surface.blit(t, rect)
        return t

    def drawMaze(self):
        cw = self.cellWidth
        ch = self.cellHeight

        for r, line in enumerate(self.maze):
            for c, cell in enumerate(line):
                x0, y0 = cw * c + self.marginLeft, ch * r + self.marginTop
                rect = (x0, y0, cw, ch)
                if cell == -1:
                    pygame.draw.rect(self.surface, self.wallColor, rect)
                else:
                    pygame.draw.rect(self.surface, self.floorColor, rect)
                    if cell != 0:
                        if cell == -2:
                            self.drawMazeIcon(self.RefreshImage, (c, r))
                        elif cell < -2:
                            self.drawMazeIcon(self.Star3Image, (c, r))
                        elif cell <= self.score1Value:
                            self.drawMazeIcon(self.Star1Image, (c, r))
                        else:
                            self.drawMazeIcon(self.Star2Image, (c, r))

    def drawMazeIcon(self, t, pos):
        m = 2
        cw = self.cellWidth
        ch = self.cellHeight

        t = pygame.transform.scale(t, (cw - 2 * m, ch - 2 * m))
        x0, y0 = cw * pos[0] + self.marginLeft, ch * pos[1] + self.marginTop
        self.surface.blit(t, (x0 + m, y0 + m))

    def drawPlayers(self):
        self.drawMazeIcon(self.P1Image, self.player1Position)
        if self.player2:
            self.drawMazeIcon(self.P2Image, self.player2Position)

    def drawEnd(self):
        font = pygame.font.Font(None, 74)
        text = font.render(f"Fin de partie.", True, (255, 255, 0))
        text_rect = text.get_rect(center=(self.windowWidth // 2, self.windowHeight // 2))
        background_rect = pygame.Rect(text_rect.left - 40, text_rect.top - 40, text_rect.width + 80, text_rect.height + 80)
        pygame.draw.rect(self.surface, (0, 0, 255), background_rect)
        self.surface.blit(text, text_rect)

    def drawRemainingTime(self, r):
        r = round(r)
        font = pygame.font.Font(None, 74)
        text = font.render(f"Début dans: " + str(r), True, (255, 255, 0))
        text_rect = text.get_rect(center=(self.windowWidth // 2, self.windowHeight // 2))
        background_rect = pygame.Rect(text_rect.left - 40, text_rect.top - 40, text_rect.width + 80, text_rect.height + 80)
        pygame.draw.rect(self.surface, (0, 0, 255), background_rect)
        self.surface.blit(text, text_rect)

    def draw(self):
        self.surface.fill(self.bgColor)
        self.drawMargin()
        self.drawMaze()
        self.drawPlayers()
        if self.currentStep >= self.steps:
            self.drawEnd()
        if not self.runTimeElapsed:
            self.drawRemainingTime(self.delayToRun - time.time() + self.runTime)
        pygame.display.flip()

    @staticmethod
    def genMaze(width, height, rnd: random.Random):
        w, h = (width - 1) // 2, (height - 1) // 2
        maze = np.ones((h*2+1, w*2+1))

        x, y = (0, 0)
        maze[2*y+1, 2*x+1] = 0

        stack = [(y, x)]
        while len(stack) > 0:
            y, x = stack[-1]

            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
            rnd.shuffle(directions)

            for dy, dx in directions:
                ny, nx = y + dy, x + dx
                if nx >= 0 and ny >= 0 and nx < w and ny < h and maze[2*ny+1, 2*nx+1] == 1:
                    maze[2*ny+1, 2*nx+1] = 0
                    maze[2*y+1+dy, 2*x+1+dx] = 0
                    stack.append((ny, nx))
                    break
            else:
                stack.pop()

        #maze[1, 0] = 0
        #maze[-2, -1] = 0

        return maze * -1

    def genPlayerPosition(self):
        x = self.random.randrange(self.width)
        y = self.random.randrange(self.height)

        while self.maze[y][x] != 0 or (x, y) == self.player1Position or (x, y) == self.player2Position:
            x += 1
            if x >= self.width:
                x = 0
                y = (y + 1) % self.height

        return (x, y)

    def generateMazeCells(self, minValue, maxValue, count):
        for _ in range(count):
            x, y = self.genPlayerPosition()
            self.maze[y][x] = self.random.randrange(minValue, maxValue + 1)

    def generateMazeCellsForScore1(self, count):
        self.generateMazeCells(1, self.score1Value, count)

    def generateMazeCellsForScore2(self, count):
        self.generateMazeCells(self.score1Value + 1, self.score2Value, count)

    def generateMazeCellsForScoreMin(self, count):
        self.generateMazeCells(self.scoreMinValue, -3, count)

    def generateMazeCellsForRefresh(self, count):
        if self.enableRPCGame:
            self.generateMazeCells(-2, -2, count)

    def isValidPosFrom(self, p0, p1):
        if p0 == p1:
            return False
        if self.maze[p1[1]][p1[0]] == -1:
            return False
        if p0[0] == p1[0]:
            return abs(p1[1] - p0[1]) == 1
        elif p0[1] == p1[1]:
            return abs(p1[0] - p0[0]) == 1
        else:
            return False

    def playScoreSound(self, x, y):
        if not self.playSounds:
            return
        oldCell = self.maze[y][x]
        if oldCell == -2:
            self.RefreshSound.stop()
            self.RefreshSound.play()
        elif oldCell < 0:
            self.Star3Sound.stop()
            self.Star3Sound.play()
        elif oldCell > 0:
            if oldCell <= self.score1Value:
                self.Star1Sound.stop()
                self.Star1Sound.play()
            else:
                self.Star2Sound.stop()
                self.Star2Sound.play()

    def processPoints(self):
        x1, y1 = self.player1Position
        cell1 = self.maze[y1][x1]
        x2, y2 = self.player2Position
        cell2 = self.maze[y2][x2]
        if cell1:
            if cell1 == -2:
                if self.enableRPCGame:
                    pass
                self.player1Type = (self.player1Type + self.random.choice([1, 2])) % len(self.TYPES)
            else:
                self.player1Score += cell1
            self.playScoreSound(x1, y1)
            self.replaceMazeCell(x1, y1)
        if cell2:
            if cell2 == -2:
                if self.enableRPCGame:
                    pass
                self.player2Type = (self.player2Type + self.random.choice([1, 2])) % len(self.TYPES)
            else:
                self.player2Score += cell2
            if self.player1Position != self.player2Position:
                self.playScoreSound(x2, y2)
                self.replaceMazeCell(x2, y2)
        if self.player2 and self.enableRPCGame and self.player1Position == self.player2Position:
            c = self.compareTypes(self.player1Type, self.player2Type)
            if c > 0:
                self.player1Score += self.scoreCrossValue
                self.player2Position = (-1, -1)
                self.player2Position = self.genPlayerPosition()
                if self.playSounds:
                    self.CrossSound.stop()
                    self.CrossSound.play()
            elif c < 0:
                self.player2Score += self.scoreCrossValue
                self.player1Position = (-1, -1)
                self.player1Position = self.genPlayerPosition()
                if self.playSounds:
                    self.CrossSound.stop()
                    self.CrossSound.play()

    def randomMove(self, pos0):
        x, y = pos0
        moves = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        self.random.shuffle(moves)
        for p in moves:
            if self.isValidPosFrom(pos0, p):
                return p
        return pos0

    def replaceMazeCell(self, x, y):
        oldCell = self.maze[y][x]
        self.maze[y][x] = 0
        if not self.regenerateCells:
            return
        if oldCell == -2:
            self.generateMazeCellsForRefresh(1)
        elif oldCell < 0:
            self.generateMazeCellsForScoreMin(1)
        elif oldCell > 0:
            if oldCell <= self.score1Value:
                self.generateMazeCellsForScore1(1)
            else:
                self.generateMazeCellsForScore2(1)

    def registerPlayers(self, player1: BasePlayer, player2: BasePlayer = None):
        if self.player1 or self.player2:
            raise AttributeError('Players already set !')
        self.player1 = player1
        self.player2 = player2

        font = pygame.font.Font(None, 56)
        self.player1Text = font.render(self.player1.name, True, self.player1Color)
        if self.player2:
            self.player2Text = font.render(self.player2.name, True, self.player2Color)

    def runPlayer(self, player: BasePlayer, myPos, enemyPos, myType, enemyType, myScore, enemyScore):
        try:
            print('Le joueur "' + player.name + '" joue')

            timeout = 1 + (self.maxTime // 1000)
            if self.useAlarmSignal:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            start_time = time.time()
            try:
                p = player.play(np.copy(self.maze), myPos, enemyPos, myType, enemyType, myScore, enemyScore)
            except TimeoutError:
                print('Le joueur ' + player.name + ' a trop tardé ... Une pénalité de score est appliquée.')
                return (self.scoreOnTimeout, self.randomMove(myPos))
            finally:
                if self.useAlarmSignal:
                    signal.alarm(0)
            if (time.time() - start_time) * 1000 > self.maxTime:
                print('Le joueur ' + player.name + ' a trop tardé ... Une pénalité de score est appliquée.')
                return (self.scoreOnTimeout, self.randomMove(myPos))
            if not self.isValidPosFrom(myPos, p):
                print('Le joueur ' + player.name + ' a retourné une position invalide (' + str(myPos) + '->' + str(p) + ') ... Une pénalité de score est appliquée.')
                return (self.scoreOnBadMove, self.randomMove(myPos))
            return (0, p)
        except Exception as e:
            print('Le joueur ' + player.name + ' a émi une exception ... Une pénalité de score est appliquée.')
            print('Exception: ', e)
            traceback.print_exc()
            return (self.scoreOnException, self.randomMove(myPos))

    def run(self):
        self.running = True
        self.runTime = time.time()
        self.draw()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.windowWidth = event.w
                    self.windowHeight = event.h
                    self.createSurface()
                    self.draw()

            if not self.runTimeElapsed:
                self.draw()
                self.runTimeElapsed = time.time() - self.runTime >= self.delayToRun
            elif self.currentStep < self.steps:
                self.currentStep += 1
                s, p = self.runPlayer(
                    self.player1, self.player1Position, self.player2Position,
                    self.player1Type, self.player2Type,
                    self.player1Score, self.player2Score
                )
                self.player1Score += s
                self.player1Position = p
                if self.player2:
                    s, p = self.runPlayer(
                        self.player2, self.player2Position, self.player1Position,
                        self.player2Type, self.player1Type,
                        self.player2Score, self.player1Score
                    )
                    self.player2Score += s
                    self.player2Position = p

                self.processPoints()

                self.draw()
            pygame.time.wait(self.stepDelay)
        pygame.quit()

class BasePlayer:
    def __init__(self, config: ChallengeConfig) -> None:
        """
            challengeConfig: Various information about the challenge that you can access (including width, height, stepsMax, etc.).
        """
        self.name = 'No name given'
        self.config = config

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
        """
        Joue un coup dans le jeu en retournant la prochaine position où devra aller le joueur.

        Parameters:
            maze (numpy.ndarray): Un tableau numpy 2D représentant le labyrinthe où le jeu se déroule.
                Pour obtenir la cellule à la position (x, y), utilisez `maze[y][x]`.
            myPosition (tuple[int, int]): Un tuple représentant la position actuelle du joueur dans le labyrinthe.
            enemyPosition (tuple[int, int]): Un tuple représentant la position actuelle du joueur adverse.
            myType (int): Un entier représentant le type de joueur contrôlé par la fonction (l'un de : TYPE_PIERRE, TYPE_CISEAU, TYPE_FEUILLE).
            enemyType (int): Un entier représentant le type de joueur adverse (l'un de : TYPE_PIERRE, TYPE_CISEAU, TYPE_FEUILLE).
            myScore (int): Un entier représentant le score actuel du joueur contrôlé.
            enemyScore (int): Un entier représentant le score actuel du joueur adverse.

        Returns:
            tuple[int, int]: Un tuple représentant le prochain mouvement à effectuer par le joueur contrôlé par la fonction.
                Le tuple contient deux entiers représentant les coordonnées (x, y) de la prochaine position.

        Remarques :
            - La fonction est censée analyser l'état du jeu fourni par les paramètres et décider du prochain mouvement.
            - La fonction doit retourner une position valide, qui différe de la position précédente d'une seule case (sur les x ou y exclusivement).
            - Si vous renvoyez un mauvais mouvement (aller dans un mur par exemple), une pénalité de score est appliquée et un mouvement aléatoire est joué.
            - Si une exception se produit, une pénalité de score est appliquée et un mouvement aléatoire est joué.
            - Si la fonction est trop lente, une pénalité de score est appliquée et un mouvement aléatoire est joué.
            - Les types de cellules du labyrinthe sont les suivants :
                - (-1) indique un mur
                - (-2) indique une cellule de rafraîchissement, passer par cette cellule changera le type du joueur de manière aléatoire.
                - tout autre nombre est une cellule libre où le joueur obtient le score donné (peut être positif ou négatif !)
            - Si votre type de joueur est gagnant sur le type de l'adversaire (exemple Feuille > Pierre), alors si vous passez sur
                la même case que l'adversaire, vous gagnez un bonus de points et l'adversaire est déplacé vers une case aléatoire dans le labyrinth.
        """
        return (1, 1)

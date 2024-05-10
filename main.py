# Ceci est le code principal du jeu
# Ceci ne peut être modifié que par les organisateurs de l'événement ou lors de vos tests

from __future__ import annotations
from challenge import Challenge

from playerExample1 import Player as Player1
from playerExample2 import Player as Player2

def main():
    challenge = Challenge(
        title='Challenge CSI',
        width=40,
        height=30,
        delayToRun=5, # Nombre de secondes avant de démarrer la simulation
        steps=1000, # Nombre d'étapes à simuler
        stepDelay=0, # Durée en millisecondes pour passer à l'étape suivante (augmenter pour ralentir)

        # Mode de jeu
        enableRPCGame=True, # Mettre à False pour désactiver le mode Papier-Pierre-Ciseaux
        regenerateCells=False, # Mettre à True pour immediatement ajouter d'autres bonus, lorsqu'ils sont consommés
        randomSeed=None, # Mettre un nombre, pour générer une partie identique à chaque fois,
        playSounds=False, # Mettre à False pour ne pas jouer les sons

        # Réglage des scores et des pénalités
        score1Value=3, # Score maximal (etoiles jaunes)
        countScore1=0.25, # Nombres d'étoiles jaunes (ratio (0.25 = 25%))
        score2Value=11, # Score maximal (etoiles vertes)
        countScore2=0.10, # Nombres d'étoiles vertes (ratio (0.10 = 10%))
        scoreMinValue=-10, # Score minimal (etoiles noires)
        countScoreMin=0.15, # Nombres d'étoiles noires (ratio (0.15 = 15%))
        scoreCrossValue=17, # Score si vous passez sur la même case que l'adversaire avec un type gagnant (ex: pierre > ciseaux)
        scoreOnBadMove=-35, # Pénalité si un coup illégal est retourné
        scoreOnException=-50, # Pénalité si une exception survient
        scoreOnTimeout=-13, # Pénalité si le joueur met trop de temps à jouer
        maxTime=500, # Si le joueur prend plus de temps que ce qui est donné ici en millisecondes, alors un coup aléatoire est joué et une pénalité est appliquée
    )

    player1 = Player1(challenge.cloneConfig())
    player2 = Player2(challenge.cloneConfig()) # mettre à None, pour un seul joueur

    challenge.registerPlayers(player1, player2)

    challenge.run()

if __name__ == "__main__":
    main()

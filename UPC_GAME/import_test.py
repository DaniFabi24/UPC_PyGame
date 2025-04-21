# /home/Daniel/UPC_PyGame/UPC_GAME/import_test.py
try:
    from UPC_GAME.core.game_world import GameWorld
    print("GameWorld importiert erfolgreich!")
    game_world = GameWorld(800, 600)
    print(f"GameWorld Instanz erstellt: {game_world}")
except ImportError as e:
    print(f"Fehler beim Importieren von GameWorld: {e}")
except Exception as e:
    print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
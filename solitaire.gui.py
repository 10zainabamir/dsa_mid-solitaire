import os
import re
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageTk
from my_solitaire import Game, SUITS, RANKS

# ---------------- sizes (in pixels) ----------------
CARD_W = 96          # width of one card
GAP = 20             # space between columns
MARGIN = 20          # space around the board
TOP = 16             # top row (stock, waste, foundations) starts here
OFFSET_DOWN = 16     # how far apart face-down cards are in a pile
OFFSET_UP = 32       # how far apart face-up cards are in a pile
CANVAS_H = 500       # height of the playing area
GREEN = "#0b6b3a"
LINE = "#3fae78"

RANK_NAMES = {'A': 'ace', 'J': 'jack', 'Q': 'queen', 'K': 'king'}
SUIT_NAMES = {'H': 'hearts', 'D': 'diamonds', 'C': 'clubs', 'S': 'spades'}
SUIT_SYMBOLS = {'H': '\u2665', 'D': '\u2666', 'C': '\u2663', 'S': '\u2660'}


# ---------------- loading the pictures ----------------
def find_pictures():
    """Search the folder of this file (and the folders inside it) for
    picture files.  Returns {'king_of_spades': 'C:\\...\\king_of_spades2.jpg', ...}"""
    here = os.path.dirname(os.path.abspath(__file__))
    pictures = {}
    for folder, subfolders, files in os.walk(here):
        subfolders[:] = [f for f in subfolders if f not in ('venv', '.venv', '__pycache__')]
        for name in files:
            stem, ext = os.path.splitext(name)
            if ext.lower() in ('.jpg', '.jpeg', '.png'):
                stem = re.sub(r'(?<=[a-z])\d+$', '', stem.lower())  # jack_of_clubs2 -> jack_of_clubs
                pictures.setdefault(stem, os.path.join(folder, name))
    return pictures


def load_card_images():
    """Returns {'KS': picture, 'AH': picture, ...} for all 52 cards."""
    pictures = find_pictures()
    cards = {}
    for rank in RANKS:
        for suit in SUITS:
            name = f"{RANK_NAMES.get(rank, rank)}_of_{SUIT_NAMES[suit]}"
            if name not in pictures:
                raise SystemExit(f"Picture not found: {name}\n"
                                 f"Is the card_images folder next to this file?")
            cards[rank + suit] = Image.open(pictures[name]).convert("RGB")
    return cards


def make_back(w, h):
    """The downloaded set has no card back, so draw a simple one."""
    back = Image.new("RGB", (w, h), "white")
    pen = ImageDraw.Draw(back)
    pen.rectangle([5, 5, w - 6, h - 6], fill="#1f3c88")
    pen.rectangle([12, 12, w - 13, h - 13], outline="white")
    pen.rectangle([0, 0, w - 1, h - 1], outline="#555555")
    return back


# ---------------- the window ----------------
class SolitaireApp:
    def __init__(self, root):
        self.root = root
        root.title("Klondike Solitaire")

        # card pictures, resized to the card size
        raw = load_card_images()
        w, h = raw['AH'].size
        self.card_w = CARD_W
        self.card_h = int(CARD_W * h / w)          # keep the picture's shape
        self.faces = {}
        for key, img in raw.items():
            self.faces[key] = ImageTk.PhotoImage(img.resize((self.card_w, self.card_h)))
        self.back = ImageTk.PhotoImage(make_back(self.card_w, self.card_h))

        self.tab_top = TOP + self.card_h + 30       # tableau starts below the top row
        canvas_w = 2 * MARGIN + 7 * self.card_w + 6 * GAP

        # top bar with buttons
        bar = tk.Frame(root, bg="#073d21")
        bar.pack(fill="x")
        tk.Button(bar, text="New Game", command=self.new_game).pack(side="left", padx=6, pady=6)
        tk.Button(bar, text="Undo", command=self.undo).pack(side="left", padx=3)
        tk.Button(bar, text="Redo", command=self.redo).pack(side="left", padx=3)
        self.draw_var = tk.IntVar(value=1)
        for n in (1, 3):
            tk.Radiobutton(bar, text=f"Draw {n}", variable=self.draw_var, value=n,
                           command=self.change_draw, bg="#073d21", fg="white",
                           selectcolor="#073d21", activebackground="#073d21",
                           activeforeground="white").pack(side="left", padx=6)
        self.info = tk.Label(bar, bg="#073d21", fg="white", font=("Segoe UI", 11))
        self.info.pack(side="right", padx=12)

        # playing area
        self.canvas = tk.Canvas(root, width=canvas_w, height=CANVAS_H,
                                bg=GREEN, highlightthickness=0)
        self.canvas.pack()

        # message line at the bottom
        self.status = tk.StringVar(value="Drag cards. Click the stock to draw. "
                                         "Double-click a card to send it to the foundation.")
        tk.Label(root, textvariable=self.status, anchor="w", bg="#073d21",
                 fg="white", padx=10).pack(fill="x")

        root.resizable(False, False)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        root.bind("<Control-z>", lambda e: self.undo())
        root.bind("<Control-y>", lambda e: self.redo())

        self.game = Game(1)
        self.drag = None        # info about the card(s) being dragged
        self.spots = []         # clickable areas, filled in by draw_board()
        self.draw_board()
        self.tick()

    # ---------- small helpers ----------
    def column_x(self, i):
        """Left edge of column i (0..6)."""
        return MARGIN + i * (self.card_w + GAP)

    def tick(self):
        """Updates the moves / timer text twice a second."""
        seconds = int(time.time() - self.game.start_time)
        self.info.config(text=f"Moves: {self.game.moves}    "
                              f"Time: {seconds // 60:02d}:{seconds % 60:02d}")
        self.root.after(500, self.tick)

    def spacing(self, cards):
        """Gaps between the cards of one pile. Very tall piles are squeezed to fit."""
        down = sum(1 for c in cards if not c.face_up)
        up = len(cards) - down
        needed = down * OFFSET_DOWN + max(up - 1, 0) * OFFSET_UP
        free = CANVAS_H - self.tab_top - self.card_h - 8
        if needed > free:
            shrink = free / needed
            return OFFSET_DOWN * shrink, OFFSET_UP * shrink
        return OFFSET_DOWN, OFFSET_UP

    def draw_slot(self, x, y, symbol=""):
        """Empty dashed rectangle (an empty pile)."""
        self.canvas.create_rectangle(x, y, x + self.card_w, y + self.card_h,
                                     outline=LINE, width=2, dash=(5, 4))
        if symbol:
            self.canvas.create_text(x + self.card_w / 2, y + self.card_h / 2, text=symbol,
                                    fill=LINE, font=("Segoe UI Symbol", 28))

    # ---------- drawing the whole board ----------
    def draw_board(self):
        game = self.game
        canvas = self.canvas
        canvas.delete("all")
        self.spots = []

        # cards that are being dragged are not drawn in their old place
        hidden = self.drag if (self.drag and self.drag["moved"]) else None

        # stock (top-left)
        x, y = self.column_x(0), TOP
        if game.stock.size() > 0:
            canvas.create_image(x, y, image=self.back, anchor="nw")
        else:
            self.draw_slot(x, y, "\u21bb")          # circular arrow = click to recycle
        canvas.create_text(x + self.card_w / 2, y + self.card_h + 12,
                           text=f"Stock: {game.stock.size()}", fill="white")
        self.spots.append(dict(kind="stock", rect=(x, y, x + self.card_w, y + self.card_h)))

        # waste (shows the last 3 cards fanned out when drawing 3)
        waste = game.waste.to_list()
        if hidden and hidden["src"] == ("w",):
            waste = waste[:-1]
        shown = waste[-3:] if game.draw_count == 3 else waste[-1:]
        if not shown:
            self.draw_slot(self.column_x(1), TOP)
        for k, card in enumerate(shown):
            x = self.column_x(1) + k * 22
            canvas.create_image(x, TOP, image=self.faces[card.key()], anchor="nw")
            if k == len(shown) - 1:                  # only the top card can be picked up
                self.spots.append(dict(kind="waste", card=card,
                                       rect=(x, TOP, x + self.card_w, TOP + self.card_h)))

        # 4 foundation piles (top-right)
        for k, suit in enumerate(SUITS):
            x = self.column_x(3 + k)
            pile = game.foundation[suit].to_list()
            if hidden and hidden["src"] == ("f", suit):
                pile = pile[:-1]
            if pile:
                canvas.create_image(x, TOP, image=self.faces[pile[-1].key()], anchor="nw")
                self.spots.append(dict(kind="found", suit=suit, card=pile[-1],
                                       rect=(x, TOP, x + self.card_w, TOP + self.card_h)))
            else:
                self.draw_slot(x, TOP, SUIT_SYMBOLS[suit])

        # 7 tableau piles
        for i, linked_list in enumerate(game.tableau):
            all_cards = linked_list.to_list()
            gap_down, gap_up = self.spacing(all_cards)
            cards = all_cards
            if hidden and hidden["src"] == ("t", i):
                cards = all_cards[:len(all_cards) - hidden["n"]]
            x = self.column_x(i)
            y = self.tab_top
            if not cards:
                self.draw_slot(x, y)
            for index, card in enumerate(cards):
                image = self.faces[card.key()] if card.face_up else self.back
                canvas.create_image(x, y, image=image, anchor="nw")
                self.spots.append(dict(kind="tab", pile=i, index=index, card=card,
                                       gap=gap_up, rect=(x, y, x + self.card_w, y + self.card_h)))
                y += gap_up if card.face_up else gap_down

    # ---------- buttons ----------
    def finish_action(self, message):
        """Called after every move: redraw, show the message, check for a win."""
        self.drag = None
        self.canvas.delete("drag")
        self.draw_board()
        self.status.set(message)
        if self.game.is_won():
            if messagebox.askyesno("You won!", f"You won in {self.game.moves} moves!\n\nPlay again?"):
                self.new_game()

    def new_game(self):
        self.game = Game(self.draw_var.get())
        self.finish_action("New game started.")

    def change_draw(self):
        self.game.draw_count = self.draw_var.get()
        self.finish_action(f"Now drawing {self.game.draw_count} card(s) at a time.")

    def undo(self):
        self.finish_action(self.game.undo()[1])

    def redo(self):
        self.finish_action(self.game.redo()[1])

    # ---------- mouse ----------
    def spot_at(self, x, y):
        """Which clickable area is under the mouse? (topmost card first)"""
        for spot in reversed(self.spots):
            x1, y1, x2, y2 = spot["rect"]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return spot
        return None

    def source_of(self, spot):
        """Turns a clicked spot into (source, number_of_cards) for game.move()."""
        if spot["kind"] == "waste":
            return ("w",), 1
        if spot["kind"] == "found":
            return ("f", spot["suit"]), 1
        if spot["kind"] == "tab" and spot["card"].face_up:
            pile = self.game.tableau[spot["pile"]]
            return ("t", spot["pile"]), pile.size - spot["index"]
        return None

    def on_press(self, event):
        self.drag = None
        spot = self.spot_at(event.x, event.y)
        if spot is None:
            return
        if spot["kind"] == "stock":
            self.finish_action(self.game.draw()[1])
            return
        picked = self.source_of(spot)
        if picked is None:
            self.status.set("That card is face down.")
            return
        src, n = picked
        cards = self.game._peek_cards(src, n)        # None if these cards can't be lifted
        if cards is None:
            self.status.set("You can't pick up those cards.")
            return
        left, top = spot["rect"][0], spot["rect"][1]
        self.drag = dict(src=src, n=n, cards=cards, moved=False,
                         start_x=event.x, start_y=event.y,
                         last_x=event.x, last_y=event.y,
                         left=left, top=top,
                         grab_x=event.x - left, grab_y=event.y - top,
                         gap=spot.get("gap", 0))

    def on_motion(self, event):
        d = self.drag
        if d is None:
            return
        if not d["moved"]:
            if abs(event.x - d["start_x"]) + abs(event.y - d["start_y"]) < 5:
                return                                # too small, still just a click
            d["moved"] = True
            self.draw_board()                         # redraw without the dragged cards
            for k, card in enumerate(d["cards"]):     # floating copies that follow the mouse
                self.canvas.create_image(d["left"], d["top"] + k * d["gap"],
                                         image=self.faces[card.key()], anchor="nw", tags="drag")
        self.canvas.move("drag", event.x - d["last_x"], event.y - d["last_y"])
        d["last_x"], d["last_y"] = event.x, event.y
        self.canvas.tag_raise("drag")

    def on_release(self, event):
        d = self.drag
        self.drag = None
        if d is None or not d["moved"]:
            return                                    # it was only a click
        # centre of the first dragged card decides where it landed
        x = event.x - d["grab_x"] + self.card_w / 2
        y = event.y - d["grab_y"] + self.card_h / 2
        if y < self.tab_top - 5:                      # top row -> foundation area
            dest = ("f",) if x > self.column_x(3) - GAP else None
        else:                                         # lower area -> nearest column
            column = int((x - MARGIN + GAP / 2) // (self.card_w + GAP))
            dest = ("t", max(0, min(6, column)))
        if dest is None or dest == d["src"]:
            self.finish_action("")                    # nothing to do, put the cards back
            return
        self.finish_action(self.game.move(d["src"], dest, d["n"])[1])

    def on_double_click(self, event):
        self.drag = None
        spot = self.spot_at(event.x, event.y)
        if spot is None:
            return
        if spot["kind"] == "stock":
            self.finish_action(self.game.draw()[1])
            return
        picked = self.source_of(spot)
        if picked is None or spot["kind"] == "found":
            return
        src, n = picked
        if n != 1:                                    # only a single (top) card
            return
        self.finish_action(self.game.move(src, ("f",), 1)[1])


def main():
    root = tk.Tk()
    SolitaireApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
import random
import time

SUITS = ['H', 'D', 'C', 'S']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


# ---------------------------------------------------------------
# Step 1: Card
# ---------------------------------------------------------------
class Card:
    def __init__(self, suit, rank, face_up=False):
        self.suit = suit
        self.rank = rank
        self.face_up = face_up

    def flip(self):
        self.face_up = not self.face_up

    def value(self):                       # A=1 ... K=13
        if self.rank == 'A': return 1
        if self.rank == 'J': return 11
        if self.rank == 'Q': return 12
        if self.rank == 'K': return 13
        return int(self.rank)

    def color(self):
        return 'red' if self.suit in ('H', 'D') else 'black'

    def key(self):                         # e.g. "10H"
        return f"{self.rank}{self.suit}"

    def __str__(self):                     # what print() shows
        return self.key() if self.face_up else "XX"


# ---------------------------------------------------------------
# Step 2: ArrayList and Deck
# ---------------------------------------------------------------
class ArrayList:
    def __init__(self):
        self._items = []

    def append(self, item):  self._items.append(item)
    def get(self, i):        return self._items[i]
    def set(self, i, item):  self._items[i] = item

    def pop(self):
        return self._items.pop() if self._items else None

    def size(self):          return len(self._items)
    def is_empty(self):      return len(self._items) == 0


class Deck:
    def __init__(self):
        self.cards = ArrayList()
        for suit in SUITS:
            for rank in RANKS:
                self.cards.append(Card(suit, rank))

    def shuffle(self):                     # Fisher-Yates
        for i in range(self.cards.size() - 1, 0, -1):
            j = random.randint(0, i)
            tmp = self.cards.get(i)
            self.cards.set(i, self.cards.get(j))
            self.cards.set(j, tmp)

    def draw(self):
        return self.cards.pop()

    def is_empty(self):
        return self.cards.is_empty()


# ---------------------------------------------------------------
# Step 3: Stack
# ---------------------------------------------------------------
class Stack:
    def __init__(self):
        self._items = []

    def push(self, item): self._items.append(item)
    def pop(self):        return self._items.pop() if self._items else None
    def peek(self):       return self._items[-1] if self._items else None
    def is_empty(self):   return len(self._items) == 0
    def size(self):       return len(self._items)
    def to_list(self):    return list(self._items)    # bottom -> top


# ---------------------------------------------------------------
# Step 4: Queue
# ---------------------------------------------------------------
class Queue:
    def __init__(self):
        self._items = []
        self._head = 0                     # index of the front item

    def enqueue(self, item):
        self._items.append(item)

    def dequeue(self):
        if self.is_empty():
            return None
        item = self._items[self._head]
        self._head += 1
        return item

    def is_empty(self):
        return self._head >= len(self._items)

    def size(self):
        return len(self._items) - self._head

    def to_list(self):                     # front -> back
        return self._items[self._head:]


# ---------------------------------------------------------------
# Step 5: Linked List
# ---------------------------------------------------------------
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None
        self.size = 0

    def append(self, data):                # add on top (end of chain)
        node = Node(data)
        if self.head is None:
            self.head = node
        else:
            cur = self.head
            while cur.next is not None:
                cur = cur.next
            cur.next = node
        self.size += 1

    def peek_last(self):                   # top card
        if self.head is None:
            return None
        cur = self.head
        while cur.next is not None:
            cur = cur.next
        return cur.data

    def split_from(self, index):           # cut the chain, return the cut-off cards
        if index < 0 or index >= self.size:
            return []
        if index == 0:
            cur = self.head
            self.head = None
        else:
            prev = self.head
            for _ in range(index - 1):
                prev = prev.next
            cur = prev.next
            prev.next = None
        removed = []
        while cur is not None:
            removed.append(cur.data)
            cur = cur.next
        self.size = index
        return removed

    def to_list(self):
        res = []
        cur = self.head
        while cur is not None:
            res.append(cur.data)
            cur = cur.next
        return res


# ---------------------------------------------------------------
# Steps 6-10: Game
# ---------------------------------------------------------------
class Game:
    # ----- Step 6: setup -----
    def __init__(self, draw_count=1):
        self.draw_count = draw_count
        self.new_game()

    def new_game(self):
        deck = Deck()
        deck.shuffle()
        self.tableau    = [LinkedList() for _ in range(7)]
        self.foundation = {s: Stack() for s in SUITS}
        self.waste      = Stack()
        self.stock      = Queue()
        self.undo_stack = Stack()
        self.redo_stack = Stack()
        self.moves = 0
        self.start_time = time.time()

        for i in range(7):                 # pile i gets i+1 cards
            for j in range(i + 1):
                card = deck.draw()
                card.face_up = (j == i)    # only the last is face up
                self.tableau[i].append(card)

        while not deck.is_empty():         # the rest -> stock
            card = deck.draw()
            card.face_up = False
            self.stock.enqueue(card)

        self.update_positions()

    def update_positions(self):            # the Dictionary
        self.positions = {}
        for i, pile in enumerate(self.tableau):
            for j, c in enumerate(pile.to_list()):
                self.positions[c.key()] = (f"Tableau {i+1}, card {j+1}", c.face_up)
        for s in SUITS:
            for c in self.foundation[s].to_list():
                self.positions[c.key()] = (f"Foundation {s}", True)
        for c in self.waste.to_list():
            self.positions[c.key()] = ("Waste pile", c.face_up)
        for c in self.stock.to_list():
            self.positions[c.key()] = ("Stock", False)

    # ----- Step 7: rules -----
    def can_go_foundation(self, card):
        top = self.foundation[card.suit].peek()
        if top is None:
            return card.value() == 1                # empty pile: only an Ace
        return card.value() == top.value() + 1      # next rank up

    def can_go_tableau(self, cards, dest):
        first = cards[0]                            # the card that touches the pile
        top = self.tableau[dest].peek_last()
        if top is None:
            return first.value() == 13              # empty column: only a King
        return (top.face_up and top.color() != first.color()
                and top.value() == first.value() + 1)

    # ----- Step 8: moving and flipping -----
    def _peek_cards(self, src, n):                  # look, don't remove
        kind = src[0]
        if kind == 'w':
            if n == 1 and not self.waste.is_empty():
                return [self.waste.peek()]
            return None
        if kind == 'f':
            p = self.foundation[src[1]]
            if n == 1 and not p.is_empty():
                return [p.peek()]
            return None
        pile = self.tableau[src[1]]
        if n < 1 or n > pile.size:
            return None
        cards = pile.to_list()[pile.size - n:]
        for c in cards:                             # all must be face up
            if not c.face_up:
                return None
        for k in range(len(cards) - 1):             # must be a valid run
            if (cards[k].color() == cards[k + 1].color()
                    or cards[k].value() != cards[k + 1].value() + 1):
                return None
        return cards

    def _remove(self, src, n):                      # actually take the cards off
        if src[0] == 'w':
            self.waste.pop()
        elif src[0] == 'f':
            self.foundation[src[1]].pop()
        else:
            pile = self.tableau[src[1]]
            pile.split_from(pile.size - n)

    def move(self, src, dest, n=1):
        cards = self._peek_cards(src, n)
        if cards is None:
            return False, "You can't pick up those card(s)."

        if dest[0] == 'f':
            if src[0] == 'f':
                return False, "Already on the foundation."
            if len(cards) != 1:
                return False, "One card at a time to the foundation."
            if not self.can_go_foundation(cards[0]):
                return False, "Can't go on the foundation yet."
        else:
            if src == ('t', dest[1]):
                return False, "Same pile."
            if not self.can_go_tableau(cards, dest[1]):
                return False, "Illegal move."

        before = self.snapshot()                    # for undo
        self._remove(src, n)
        if dest[0] == 'f':
            self.foundation[cards[0].suit].push(cards[0])
        else:
            for c in cards:
                self.tableau[dest[1]].append(c)

        if src[0] == 't':                           # FLIP the exposed card
            last = self.tableau[src[1]].peek_last()
            if last is not None and not last.face_up:
                last.flip()

        self._commit(before)
        return True, "Moved."

    def is_won(self):
        return all(self.foundation[s].size() == 13 for s in SUITS)

    # ----- Step 9: drawing from the stock -----
    def draw(self):
        if self.stock.is_empty() and self.waste.is_empty():
            return False, "No cards left."

        before = self.snapshot()

        if self.stock.is_empty():                   # recycle the waste
            for c in self.waste.to_list():          # bottom -> top = original order
                c.face_up = False
                self.stock.enqueue(c)
            self.waste = Stack()
            self._commit(before)
            return True, "Waste turned back into the stock."

        for _ in range(self.draw_count):            # draw 1 or 3 cards
            if self.stock.is_empty():
                break
            c = self.stock.dequeue()
            c.face_up = True
            self.waste.push(c)
        self._commit(before)
        return True, "Drew from the stock."

    # ----- Step 10: undo and redo -----
    def snapshot(self):
        cv = lambda c: (c.suit, c.rank, c.face_up)  # card -> plain values
        return {
            'tableau':    [[cv(c) for c in p.to_list()] for p in self.tableau],
            'foundation': {s: [cv(c) for c in self.foundation[s].to_list()] for s in SUITS},
            'waste':      [cv(c) for c in self.waste.to_list()],
            'stock':      [cv(c) for c in self.stock.to_list()],
            'moves':      self.moves,
        }

    def restore(self, snap):
        mk = lambda t: Card(t[0], t[1], t[2])       # plain values -> card
        self.tableau = []
        for pile in snap['tableau']:
            ll = LinkedList()
            for t in pile:
                ll.append(mk(t))
            self.tableau.append(ll)
        self.foundation = {}
        for s in SUITS:
            st = Stack()
            for t in snap['foundation'][s]:
                st.push(mk(t))
            self.foundation[s] = st
        self.waste = Stack()
        for t in snap['waste']:
            self.waste.push(mk(t))
        self.stock = Queue()
        for t in snap['stock']:
            self.stock.enqueue(mk(t))
        self.moves = snap['moves']
        self.update_positions()

    def _commit(self, before):
        self.undo_stack.push(before)
        self.redo_stack = Stack()                   # a new move kills redo
        self.moves += 1
        self.update_positions()

    def undo(self):
        if self.undo_stack.is_empty():
            return False, "Nothing to undo."
        self.redo_stack.push(self.snapshot())       # save the present for redo
        self.restore(self.undo_stack.pop())         # go back in time
        return True, "Undone."

    def redo(self):
        if self.redo_stack.is_empty():
            return False, "Nothing to redo."
        self.undo_stack.push(self.snapshot())
        self.restore(self.redo_stack.pop())
        return True, "Redone."

    # ----- Step 11: display -----
    def show(self):
        elapsed = int(time.time() - self.start_time)
        print("\n" + "=" * 52)
        print(f"Moves: {self.moves}   Time: {elapsed // 60:02d}:{elapsed % 60:02d}   "
              f"Draw: {self.draw_count}")
        waste_top = self.waste.peek()
        print(f"Stock: {self.stock.size()}   "
              f"Waste: {waste_top if waste_top else '--'} ({self.waste.size()})")
        print("Foundations -> " + "  ".join(
            f"{s}:{self.foundation[s].peek() or '--'}" for s in SUITS))
        print("-" * 52)
        piles = [p.to_list() for p in self.tableau]
        print("".join(f"  T{i + 1}".ljust(7) for i in range(7)))
        height = max(len(p) for p in piles)
        for r in range(height):
            row = ""
            for p in piles:
                row += (str(p[r]) if r < len(p) else "").rjust(4).ljust(7)
            print(row)
        print("=" * 52)

HELP = """
Commands
  d            draw from the stock
  w t3         move top waste card to tableau pile 3
  w f          move top waste card to its foundation
  t3 f         move top card of pile 3 to the foundation
  t3 t5        move top card of pile 3 onto pile 5
  t3 t5 4      move the last 4 cards of pile 3 onto pile 5
  fh t2        move top Hearts foundation card back to pile 2
               (fh = hearts, fd = diamonds, fc = clubs, fs = spades)
  find 10H     where is this face-up card?
  u / r        undo / redo
  n            new game
  h            help
  q            quit
Cards are rank + suit letter (H D C S): KS, 10H, AD.  XX = face down.
"""        

def parse_src(tok):
    tok = tok.lower()
    if tok == 'w':
        return ('w',)
    if len(tok) >= 2 and tok[0] == 't' and tok[1:].isdigit() and 1 <= int(tok[1:]) <= 7:
        return ('t', int(tok[1:]) - 1)          # t3 -> ('t', 2)
    if len(tok) == 2 and tok[0] == 'f' and tok[1].upper() in SUITS:
        return ('f', tok[1].upper())            # fh -> ('f', 'H')
    return None


def parse_dest(tok):
    tok = tok.lower()
    if tok == 'f':
        return ('f',)
    if len(tok) >= 2 and tok[0] == 't' and tok[1:].isdigit() and 1 <= int(tok[1:]) <= 7:
        return ('t', int(tok[1:]) - 1)
    return None


def ask_draw_count():
    while True:
        ans = input("Draw 1 or 3 cards at a time? [1/3]: ").strip()
        if ans in ('1', '3'):
            return int(ans)


def main():
    print("KLONDIKE SOLITAIRE")
    game = Game(ask_draw_count())
    print(HELP)

    while True:
        game.show()
        if game.is_won():
            print(f"*** YOU WON in {game.moves} moves! ***")
            if input("Play again? [y/n]: ").strip().lower() == 'y':
                game = Game(ask_draw_count())
                continue
            break

        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        parts = line.split()
        if not parts:
            continue
        cmd = parts[0].lower()

        if cmd == 'q':
            break
        elif cmd == 'h':
            print(HELP)
        elif cmd == 'n':
            game = Game(ask_draw_count())
        elif cmd == 'd':
            print(game.draw()[1])
        elif cmd == 'u':
            print(game.undo()[1])
        elif cmd == 'r':
            print(game.redo()[1])
        elif cmd == 'find' and len(parts) == 2:
            info = game.positions.get(parts[1].upper())
            if info is None:
                print("No such card.")
            elif not info[1]:
                print("That card is face down - hidden.")
            else:
                print(info[0])
        elif len(parts) in (2, 3):
            src = parse_src(parts[0])
            dest = parse_dest(parts[1])
            n = 1
            if len(parts) == 3:
                if not parts[2].isdigit():
                    print("Number of cards must be a number.")
                    continue
                n = int(parts[2])
            if src is None or dest is None:
                print("Didn't understand that. Type h for help.")
            else:
                print(game.move(src, dest, n)[1])
        else:
            print("Didn't understand that. Type h for help.")

    print("Thanks for playing!")


if __name__ == "__main__":
    main()        

